package host

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"sync"
	"time"
)

// Источники проектов.
const (
	SourceLocal  = "local"  // папка на машине пользователя, используется на месте
	SourceGitHub = "github" // репозиторий, скачанный целиком в external-apps
)

// Project — подключённое приложение: папка с исполняемыми файлами.
// Пользователь выбирает нужный .exe из Executables и запускает его (raw).
type Project struct {
	Name        string   `json:"name"`
	Dir         string   `json:"dir"`
	Source      string   `json:"source"`  // SourceLocal | SourceGitHub
	Version     string   `json:"version"` // github: ветка; local: из README
	Origin      string   `json:"origin,omitempty"`
	Description string   `json:"description,omitempty"`
	Executables []string `json:"executables"`
}

// Registry — потокобезопасный реестр проектов из ДВУХ источников:
//   - ЛОКАЛЬНЫЕ: подключаются по пути к папке (AddLocalProject), используются
//     на месте (ничего не копируется). Пути запоминаются и восстанавливаются
//     из файла состояния при следующем запуске.
//   - GITHUB: скачиваются целиком в externalRoot (external-apps) и
//     сканируются оттуда.
//
// Сводка о подключённых проектах сохраняется в statePath (scg-apps.json) и
// переписывается при каждом изменении реестра.
type Registry struct {
	mu           sync.RWMutex
	externalRoot string
	statePath    string
	local        map[string]*Project // подключённые локальные (по пути)
	external     map[string]*Project // скачанные с github (external-apps)
	localPaths   map[string]string   // имя → путь локального проекта
}

// NewRegistry — реестр над папкой внешних проектов и файлом состояния.
func NewRegistry(externalRoot, statePath string) *Registry {
	return &Registry{
		externalRoot: externalRoot,
		statePath:    statePath,
		local:        map[string]*Project{},
		external:     map[string]*Project{},
		localPaths:   map[string]string{},
	}
}

// ExternalRoot — папка внешних (github) проектов.
func (r *Registry) ExternalRoot() string { return r.externalRoot }

// LoadState восстанавливает подключённые ЛОКАЛЬНЫЕ проекты из файла состояния
// (их пути). Вызывается один раз при инициализации, до Rescan.
func (r *Registry) LoadState() {
	if r.statePath == "" {
		return
	}
	raw, err := os.ReadFile(r.statePath)
	if err != nil {
		return
	}
	var st stateFile
	if json.Unmarshal(raw, &st) != nil {
		return
	}
	r.mu.Lock()
	for _, p := range st.Local {
		if p.Dir == "" {
			continue
		}
		if fi, err := os.Stat(p.Dir); err == nil && fi.IsDir() {
			r.localPaths[p.Name] = p.Dir
		}
	}
	r.mu.Unlock()
}

// AddLocalProject подключает локальный проект по пути к его папке
// (используется на месте, ничего не копируется).
func (r *Registry) AddLocalProject(path string) (*Project, error) {
	abs, err := filepath.Abs(path)
	if err != nil {
		return nil, err
	}
	fi, err := os.Stat(abs)
	if err != nil || !fi.IsDir() {
		return nil, fmt.Errorf("папка %q не найдена или недоступна", path)
	}
	p := loadLocalProject(abs)
	r.mu.Lock()
	if _, ok := r.external[p.Name]; ok {
		r.mu.Unlock()
		return nil, fmt.Errorf("имя %q уже занято внешним проектом", p.Name)
	}
	if prev, ok := r.localPaths[p.Name]; ok && prev != abs {
		r.mu.Unlock()
		return nil, fmt.Errorf("имя %q уже занято локальным проектом из %s", p.Name, prev)
	}
	r.local[p.Name] = p
	r.localPaths[p.Name] = abs
	r.mu.Unlock()
	r.persistState()
	return p, nil
}

// Rescan перечитывает оба источника и сохраняет состояние. Недоступный
// локальный путь и битый проект не валят остальных.
func (r *Registry) Rescan() (loaded []string, problems []error) {
	freshExt := map[string]*Project{}
	if r.externalRoot != "" {
		l, p := scanExternalRoot(r.externalRoot, freshExt)
		loaded = append(loaded, l...)
		problems = append(problems, p...)
	}

	r.mu.RLock()
	paths := make(map[string]string, len(r.localPaths))
	for n, d := range r.localPaths {
		paths[n] = d
	}
	r.mu.RUnlock()

	freshLocal := map[string]*Project{}
	freshPaths := map[string]string{}
	for name, dir := range paths {
		fi, err := os.Stat(dir)
		if err != nil || !fi.IsDir() {
			problems = append(problems, fmt.Errorf("локальный проект %q отключён: папка %s недоступна", name, dir))
			continue
		}
		p := loadLocalProject(dir)
		p.Name = name // сохраняем имя, под которым проект был подключён
		freshLocal[name] = p
		freshPaths[name] = dir
		loaded = append(loaded, name)
	}
	sort.Strings(loaded)

	r.mu.Lock()
	r.external = freshExt
	r.local = freshLocal
	r.localPaths = freshPaths
	r.mu.Unlock()

	r.persistState()
	return loaded, problems
}

// scanExternalRoot наполняет fresh github-проектами: каждая подпапка — проект.
func scanExternalRoot(root string, fresh map[string]*Project) (loaded []string, problems []error) {
	if err := os.MkdirAll(root, 0o755); err != nil {
		return nil, []error{fmt.Errorf("папка %s: %w", root, err)}
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, []error{fmt.Errorf("папка %s: %w", root, err)}
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		p, perr := loadProject(filepath.Join(root, e.Name()), e.Name())
		if perr != nil {
			problems = append(problems, perr)
			continue
		}
		if prev, dup := fresh[p.Name]; dup {
			problems = append(problems, fmt.Errorf("проект %q объявлен дважды: %s и %s", p.Name, prev.Dir, p.Dir))
			continue
		}
		fresh[p.Name] = p
		loaded = append(loaded, p.Name)
	}
	return loaded, problems
}

// loadLocalProject собирает локальный проект из папки: имя из имени папки,
// версия из README (иначе «—»), список всех .exe.
func loadLocalProject(dir string) *Project {
	ver := "—"
	if v, ok := readmeVersion(dir); ok {
		ver = v
	}
	return &Project{
		Name:        componentNameFor("", filepath.Base(dir)),
		Dir:         dir,
		Source:      SourceLocal,
		Version:     ver,
		Origin:      dir,
		Description: "локальный проект: " + dir,
		Executables: findAllExes(dir),
	}
}

// GetProject — проект по имени (локальный или github).
func (r *Registry) GetProject(name string) (Project, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	if p, ok := r.local[name]; ok {
		return *p, true
	}
	if p, ok := r.external[name]; ok {
		return *p, true
	}
	return Project{}, false
}

// Projects — все проекты, отсортированы (сперва локальные, затем github;
// внутри — по имени).
func (r *Registry) Projects() []Project {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]Project, 0, len(r.local)+len(r.external))
	for _, p := range r.local {
		out = append(out, *p)
	}
	for _, p := range r.external {
		out = append(out, *p)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Source != out[j].Source {
			return out[i].Source < out[j].Source
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// RemoveProject отключает проект. Github-проект удаляется с диска (папка в
// external-apps); локальный лишь отвязывается — его исходная папка не трогается.
func (r *Registry) RemoveProject(name string) error {
	r.mu.RLock()
	pe, isExt := r.external[name]
	_, isLoc := r.local[name]
	extDir := ""
	if isExt {
		extDir = pe.Dir
	}
	r.mu.RUnlock()
	switch {
	case isExt:
		if err := os.RemoveAll(extDir); err != nil {
			return fmt.Errorf("удаление %s: %w", extDir, err)
		}
	case isLoc:
		r.mu.Lock()
		delete(r.localPaths, name)
		r.mu.Unlock()
	default:
		return fmt.Errorf("проект %q не найден", name)
	}
	r.Rescan()
	return nil
}

// ─────────────────────────────────────────────────────────────────────────
// Персистентность сводного состояния (scg-apps.json).
// ─────────────────────────────────────────────────────────────────────────

type stateFile struct {
	UpdatedAt string    `json:"updated_at"`
	Local     []Project `json:"local"`
	External  []Project `json:"external"`
}

// persistState переписывает файл состояния. Вызывается при каждом изменении
// реестра (в конце Rescan, после AddLocalProject).
func (r *Registry) persistState() {
	if r.statePath == "" {
		return
	}
	r.mu.RLock()
	locals := make([]Project, 0, len(r.local))
	for _, p := range r.local {
		locals = append(locals, *p)
	}
	exts := make([]Project, 0, len(r.external))
	for _, p := range r.external {
		exts = append(exts, *p)
	}
	r.mu.RUnlock()

	sort.Slice(locals, func(i, j int) bool { return locals[i].Name < locals[j].Name })
	sort.Slice(exts, func(i, j int) bool { return exts[i].Name < exts[j].Name })

	st := stateFile{
		UpdatedAt: time.Now().UTC().Format(time.RFC3339),
		Local:     locals,
		External:  exts,
	}
	raw, err := json.MarshalIndent(st, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(r.statePath, raw, 0o644)
}

// ─────────────────────────────────────────────────────────────────────────
// Версия локального проекта из README.
// ─────────────────────────────────────────────────────────────────────────

// readmeVersionRe извлекает версию вида 1.2 или 1.2.3, если рядом есть слово
// «версия»/«version» или префикс v (например «версия: 0.1.0», «v1.4»).
var readmeVersionRe = regexp.MustCompile(`(?i)(?:верси\p{L}*|version|\bv)\s*[:=]?\s*v?(\d+\.\d+(?:\.\d+)?)`)

// readmeVersion ищет версию в README проекта. Возвращает (версия, true),
// если найдена; иначе ("", false).
func readmeVersion(dir string) (string, bool) {
	for _, name := range []string{"README.md", "README.txt", "README", "readme.md", "readme.txt", "readme"} {
		raw, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			continue
		}
		if mm := readmeVersionRe.FindSubmatch(raw); mm != nil {
			return string(mm[1]), true
		}
	}
	return "", false
}
