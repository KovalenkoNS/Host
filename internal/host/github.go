package host

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

// Загрузка внешнего проекта из GitHub — максимально простой сценарий:
// пользователь указывает ТОЛЬКО ссылку на репозиторий. Хост:
//  1. скачивает архив репозитория (публичного);
//  2. сохраняет ВЕСЬ проект в подпапку общей папки external-apps/
//     (рядом с папкой components) — ничего не выбирая и не перекомпилируя;
//  3. пишет рядом файл метаданных .scg-project.json (ветка = версия, origin);
//  4. при каждом запуске хоста папка external-apps сканируется, а найденные
//     .exe показываются как список; пользователь сам выбирает, что запустить.
//
// ВНИМАНИЕ: запуск скачанного .exe означает исполнение чужого кода на машине
// хоста. Запускайте только проекты, которым доверяете. Это единственная
// функция хоста, требующая доступа в интернет.

// codeloadBase вынесен в переменную для подмены в тестах.
var codeloadBase = "https://codeload.github.com"

const (
	maxRepoZipBytes   = 256 << 20 // предел скачиваемого архива
	maxUnpackedBytes  = 1 << 30   // предел распакованного содержимого
	githubHTTPTimeout = 120 * time.Second

	// ExternalAppsDirName — имя общей папки для скачанных внешних проектов
	// (создаётся рядом с папкой components).
	ExternalAppsDirName = "external-apps"

	// projectMetaFile — файл метаданных проекта внутри его подпапки.
	// Хранит ветку (версию) и origin, чтобы восстановить их после перезапуска.
	projectMetaFile = ".scg-project.json"
)

var ghNameRe = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)

// projectMeta — сохраняемые метаданные скачанного проекта.
type projectMeta struct {
	Name         string `json:"name"`
	SourceRepo   string `json:"source_repo"` // owner/repo
	Origin       string `json:"origin"`      // github:owner/repo@branch
	Version      string `json:"version"`     // имя ветки (main/master)
	DownloadedAt string `json:"downloaded_at"`
}

// ParseGitHubRepo принимает "owner/repo", полный URL
// (https://github.com/owner/repo[.git]) или форму git@github.com:owner/repo
// и возвращает owner и repo.
func ParseGitHubRepo(input string) (owner, name string, err error) {
	s := strings.TrimSpace(input)
	s = strings.TrimSuffix(s, "/")
	lower := strings.ToLower(s)
	for _, pfx := range []string{"https://github.com/", "http://github.com/", "github.com/", "git@github.com:"} {
		if strings.HasPrefix(lower, pfx) {
			s = s[len(pfx):]
			break
		}
	}
	s = strings.TrimSuffix(s, ".git")
	parts := strings.Split(s, "/")
	if len(parts) != 2 || parts[0] == "" || parts[1] == "" {
		return "", "", fmt.Errorf("не удалось разобрать ссылку %q — ожидается owner/repo или https://github.com/owner/repo", input)
	}
	if !ghNameRe.MatchString(parts[0]) || !ghNameRe.MatchString(parts[1]) {
		return "", "", fmt.Errorf("недопустимые символы в имени репозитория %q", input)
	}
	return parts[0], parts[1], nil
}

// DownloadProject скачивает ВЕСЬ репозиторий по ссылке и сохраняет его в
// externalRoot/<owner>-<repo>/. Исполняемый файл не выбирается и component.json
// не создаётся — пользователь позже сам выберет .exe для запуска. Рядом
// пишется .scg-project.json (ветка/origin). Повторная загрузка обновляет проект.
func DownloadProject(repoInput, externalRoot string) (*Project, error) {
	owner, name, err := ParseGitHubRepo(repoInput)
	if err != nil {
		return nil, err
	}
	data, ref, err := downloadRepoZip(owner, name)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(externalRoot, 0o755); err != nil {
		return nil, fmt.Errorf("не удалось создать папку %s: %w", externalRoot, err)
	}
	folder := sanitizePathComponent(owner) + "-" + sanitizePathComponent(name)
	target := filepath.Join(externalRoot, folder)
	if err := os.RemoveAll(target); err != nil {
		return nil, fmt.Errorf("очистка %s: %w", target, err)
	}
	if err := extractRepoZip(data, target); err != nil {
		return nil, err
	}
	meta := projectMeta{
		Name:         componentNameFor("", name),
		SourceRepo:   owner + "/" + name,
		Origin:       "github:" + owner + "/" + name + "@" + ref,
		Version:      ref,
		DownloadedAt: time.Now().UTC().Format(time.RFC3339),
	}
	if err := writeProjectMeta(target, meta); err != nil {
		return nil, err
	}
	return loadProject(target, folder)
}

// writeProjectMeta сохраняет метаданные проекта в его подпапке.
func writeProjectMeta(dir string, m projectMeta) error {
	raw, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dir, projectMetaFile), raw, 0o644); err != nil {
		return fmt.Errorf("запись метаданных проекта: %w", err)
	}
	return nil
}

// readProjectMeta читает метаданные проекта (если файл есть и корректен).
func readProjectMeta(dir string) (projectMeta, bool) {
	raw, err := os.ReadFile(filepath.Join(dir, projectMetaFile))
	if err != nil {
		return projectMeta{}, false
	}
	var m projectMeta
	if err := json.Unmarshal(raw, &m); err != nil {
		return projectMeta{}, false
	}
	return m, true
}

// loadProject собирает Project из подпапки external-apps: метаданные (если
// есть) + актуальный список исполняемых файлов.
func loadProject(dir, folderName string) (*Project, error) {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}
	name := componentNameFor("", folderName)
	version := "—"
	origin := ExternalAppsDirName + "/" + folderName
	desc := "внешний проект из папки " + folderName
	repo := ""
	if meta, ok := readProjectMeta(abs); ok {
		if meta.Name != "" {
			name = meta.Name
		}
		if meta.Version != "" {
			version = meta.Version
		}
		if meta.Origin != "" {
			origin = meta.Origin
		}
		if meta.SourceRepo != "" {
			desc = "github.com/" + meta.SourceRepo
			repo = meta.SourceRepo
		}
	}
	return &Project{
		Name:        name,
		Dir:         abs,
		Source:      SourceGitHub,
		Version:     version,
		Origin:      origin,
		Repo:        repo,
		Description: desc,
		Available:   true,
		Executables: findAllExes(abs),
	}, nil
}

// downloadRepoZip скачивает архив ветки main (затем master).
func downloadRepoZip(owner, name string) (data []byte, ref string, err error) {
	client := &http.Client{Timeout: githubHTTPTimeout}
	for _, r := range []string{"main", "master"} {
		url := codeloadBase + "/" + owner + "/" + name + "/zip/refs/heads/" + r
		resp, gerr := client.Get(url)
		if gerr != nil {
			return nil, "", fmt.Errorf("GitHub недоступен (нужен интернет): %w", gerr)
		}
		if resp.StatusCode == http.StatusOK {
			data, err = io.ReadAll(io.LimitReader(resp.Body, maxRepoZipBytes+1))
			resp.Body.Close()
			if err != nil {
				return nil, "", fmt.Errorf("скачивание %s: %w", url, err)
			}
			if len(data) > maxRepoZipBytes {
				return nil, "", fmt.Errorf("архив репозитория больше предела %d МиБ", maxRepoZipBytes>>20)
			}
			return data, r, nil
		}
		resp.Body.Close()
	}
	return nil, "", fmt.Errorf("репозиторий %s/%s не найден или не публичный (пробовал ветки main, master)", owner, name)
}

// CheckRepoAvailability проверяет, доступен ли исходный репозиторий проекта
// для повторного скачивания (тот же адрес, что использует DownloadProject).
// branch — известная ветка (пусто → пробуются main и master). Возвращает
// (true, пояснение) либо (false, причина). Требует интернета; ответ быстрый
// (HEAD-запрос с коротким таймаутом), архив не скачивается.
func CheckRepoAvailability(sourceRepo, branch string) (bool, string) {
	owner, name, err := ParseGitHubRepo(sourceRepo)
	if err != nil {
		return false, err.Error()
	}
	refs := []string{"main", "master"}
	if branch != "" {
		refs = []string{branch}
	}
	client := &http.Client{Timeout: 7 * time.Second}
	last := ""
	for _, ref := range refs {
		req, rerr := http.NewRequest(http.MethodHead, codeloadBase+"/"+owner+"/"+name+"/zip/refs/heads/"+ref, nil)
		if rerr != nil {
			return false, rerr.Error()
		}
		resp, gerr := client.Do(req)
		if gerr != nil {
			return false, "GitHub недоступен (нужен интернет): " + gerr.Error()
		}
		resp.Body.Close()
		if resp.StatusCode == http.StatusOK {
			return true, "репозиторий доступен (ветка " + ref + ")"
		}
		last = fmt.Sprintf("ответ %d для ветки %s", resp.StatusCode, ref)
	}
	return false, "репозиторий недоступен или не публичный: " + last
}

// repoFromOrigin извлекает owner/repo и ветку из origin вида
// "github:owner/repo@branch". Для иных форм возвращает пустые строки.
func repoFromOrigin(origin string) (repo, branch string) {
	s := strings.TrimPrefix(origin, "github:")
	if s == origin {
		return "", ""
	}
	if i := strings.LastIndex(s, "@"); i >= 0 {
		return s[:i], s[i+1:]
	}
	return s, ""
}

// findAllExes перечисляет ВСЕ .exe в дереве проекта. Порядок детерминирован:
// сперва по глубине вложенности, затем по алфавиту. Пути — относительные,
// со слэшами (кроссплатформенно и стабильно для сравнения/показа).
func findAllExes(root string) []string {
	type cand struct {
		rel   string
		depth int
	}
	var found []cand
	_ = filepath.WalkDir(root, func(p string, d fs.DirEntry, werr error) error {
		if werr != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if strings.EqualFold(filepath.Ext(d.Name()), ".exe") {
			rel, rerr := filepath.Rel(root, p)
			if rerr != nil {
				return nil
			}
			slash := filepath.ToSlash(rel)
			found = append(found, cand{rel: slash, depth: strings.Count(slash, "/")})
		}
		return nil
	})
	sort.Slice(found, func(i, j int) bool {
		if found[i].depth != found[j].depth {
			return found[i].depth < found[j].depth
		}
		return found[i].rel < found[j].rel
	})
	out := make([]string, len(found))
	for i, c := range found {
		out[i] = c.rel
	}
	return out
}

// extractRepoZip распаковывает архив GitHub (внутри — один корневой
// каталог repo-ref/, который отбрасывается) с защитой от zip-slip
// и сохранением исполняемых битов файлов.
func extractRepoZip(data []byte, target string) error {
	zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
	if err != nil {
		return fmt.Errorf("архив повреждён: %w", err)
	}
	cleanTarget := filepath.Clean(target)
	var total int64
	for _, f := range zr.File {
		idx := strings.IndexRune(f.Name, '/')
		if idx < 0 {
			continue // корневая запись каталога
		}
		rel := f.Name[idx+1:]
		if rel == "" {
			continue
		}
		dest := filepath.Join(cleanTarget, filepath.FromSlash(rel))
		if dest != cleanTarget && !strings.HasPrefix(dest, cleanTarget+string(os.PathSeparator)) {
			return fmt.Errorf("архив содержит небезопасный путь %q (zip-slip)", f.Name)
		}
		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(dest, 0o755); err != nil {
				return err
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
			return err
		}
		rc, err := f.Open()
		if err != nil {
			return fmt.Errorf("чтение %s из архива: %w", f.Name, err)
		}
		mode := f.Mode().Perm()
		if mode == 0 {
			mode = 0o644
		}
		out, err := os.OpenFile(dest, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, mode)
		if err != nil {
			rc.Close()
			return err
		}
		n, err := io.Copy(out, io.LimitReader(rc, maxUnpackedBytes-total+1))
		rc.Close()
		out.Close()
		if err != nil {
			return fmt.Errorf("распаковка %s: %w", f.Name, err)
		}
		total += n
		if total > maxUnpackedBytes {
			return fmt.Errorf("распакованное содержимое больше предела %d МиБ", maxUnpackedBytes>>20)
		}
	}
	return nil
}

// componentNameFor приводит желаемое или репозиторное имя к допустимому
// имени компонента/проекта ([a-z0-9._-]).
func componentNameFor(want, fallback string) string {
	s := strings.TrimSpace(want)
	if s == "" {
		s = fallback
	}
	s = strings.ToLower(s)
	s = unsafeNameChar.ReplaceAllString(s, "-")
	s = strings.Trim(s, "-._")
	if s == "" {
		s = "external-project"
	}
	if len(s) > 64 {
		s = s[:64]
	}
	return s
}

var unsafeNameChar = regexp.MustCompile(`[^a-z0-9._-]`)

var unsafePathChar = regexp.MustCompile(`[^A-Za-z0-9._-]`)

func sanitizePathComponent(s string) string {
	return unsafePathChar.ReplaceAllString(s, "_")
}
