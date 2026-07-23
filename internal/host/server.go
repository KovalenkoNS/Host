package host

import (
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"os"
	"time"
)

// Server — HTTP-интерфейс хоста: JSON API + встроенный Web UI.
// Никаких внешних CDN и SPA-фреймворков: одна страница на html/template
// с точечным fetch — работает в изолированном контуре.
type Server struct {
	Registry *Registry
	Jobs     *JobManager
}

// Handler собирает маршрутизацию (Go 1.22 pattern routing).
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /", s.uiIndex)
	// Проекты (два источника: локальный путь и загрузка с GitHub).
	mux.HandleFunc("GET /api/projects", s.apiProjects)
	mux.HandleFunc("POST /api/projects/rescan", s.apiRescan)
	mux.HandleFunc("POST /api/projects/local", s.apiAddLocal)
	mux.HandleFunc("POST /api/projects/github", s.apiDownloadGitHub)
	mux.HandleFunc("POST /api/projects/{name}/run", s.apiProjectRun)
	mux.HandleFunc("POST /api/projects/{name}/remove", s.apiProjectRemove)
	mux.HandleFunc("GET /api/projects/{name}/availability", s.apiProjectAvailability)
	// Задания.
	mux.HandleFunc("GET /api/jobs", s.apiJobsList)
	mux.HandleFunc("GET /api/jobs/{id}", s.apiJobGet)
	mux.HandleFunc("POST /api/jobs/{id}/cancel", s.apiJobCancel)
	return mux
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, code int, err error) {
	writeJSON(w, code, map[string]string{"error": err.Error()})
}

func (s *Server) apiProjects(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, s.Registry.Projects())
}

func (s *Server) apiRescan(w http.ResponseWriter, _ *http.Request) {
	loaded, problems := s.Registry.Rescan()
	msgs := make([]string, 0, len(problems))
	for _, p := range problems {
		msgs = append(msgs, p.Error())
	}
	writeJSON(w, http.StatusOK, map[string]any{"loaded": loaded, "problems": msgs})
}

type addLocalBody struct {
	Dir string `json:"dir"`
}

// apiAddLocal подключает локальный проект по пути к его папке (на месте).
func (s *Server) apiAddLocal(w http.ResponseWriter, r *http.Request) {
	var in addLocalBody
	if err := readJSON(r, &in); err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	p, err := s.Registry.AddLocalProject(in.Dir)
	if err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	writeJSON(w, http.StatusOK, p)
}

type downloadGitHubBody struct {
	Repo string `json:"repo"`
}

// apiDownloadGitHub скачивает ВЕСЬ проект по ссылке в external-apps.
// Требует интернета; код репозитория исполняется на этой машине —
// загружайте только доверенные проекты.
func (s *Server) apiDownloadGitHub(w http.ResponseWriter, r *http.Request) {
	var in downloadGitHubBody
	if err := readJSON(r, &in); err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	if s.Registry.ExternalRoot() == "" {
		writeErr(w, http.StatusInternalServerError, fmt.Errorf("папка external-apps не настроена"))
		return
	}
	p, err := DownloadProject(in.Repo, s.Registry.ExternalRoot())
	if err != nil {
		writeErr(w, http.StatusBadGateway, err)
		return
	}
	s.Registry.Rescan()
	writeJSON(w, http.StatusOK, p)
}

// runProjectBody — только выбор файла: аргументы пользователем не передаются,
// файл запускается как есть по кнопке.
type runProjectBody struct {
	Executable string `json:"executable"`
}

func (s *Server) apiProjectRun(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	var in runProjectBody
	if err := readJSON(r, &in); err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	job, err := s.Jobs.StartProject(name, in.Executable)
	if err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	writeJSON(w, http.StatusAccepted, job)
}

// apiProjectAvailability — живая проверка доступности источника проекта:
//   - local  → существует ли папка по последнему указанному пути;
//   - github → отвечает ли исходный репозиторий (нужен интернет).
func (s *Server) apiProjectAvailability(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	p, ok := s.Registry.GetProject(name)
	if !ok {
		writeErr(w, http.StatusNotFound, fmt.Errorf("проект %q не подключён", name))
		return
	}
	available := false
	detail := ""
	switch p.Source {
	case SourceLocal:
		if fi, err := os.Stat(p.Dir); err == nil && fi.IsDir() {
			available, detail = true, "папка на месте"
		} else {
			detail = "папка недоступна — последний указанный путь: " + p.Dir
		}
	default:
		repo := p.Repo
		branch := ""
		if repo == "" {
			repo, branch = repoFromOrigin(p.Origin)
		} else if p.Version != "" && p.Version != "—" {
			branch = p.Version
		}
		if repo == "" {
			detail = "исходный репозиторий неизвестен (нет метаданных .scg-project.json)"
		} else {
			available, detail = CheckRepoAvailability(repo, branch)
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"name":       name,
		"source":     p.Source,
		"available":  available,
		"detail":     detail,
		"checked_at": time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) apiProjectRemove(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	if err := s.Registry.RemoveProject(name); err != nil {
		writeErr(w, http.StatusNotFound, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"removed": name})
}

func (s *Server) apiJobsList(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, s.Jobs.List())
}

func (s *Server) apiJobGet(w http.ResponseWriter, r *http.Request) {
	j, ok := s.Jobs.Get(r.PathValue("id"))
	if !ok {
		writeErr(w, http.StatusNotFound, fmt.Errorf("задание не найдено"))
		return
	}
	writeJSON(w, http.StatusOK, j)
}

func (s *Server) apiJobCancel(w http.ResponseWriter, r *http.Request) {
	if !s.Jobs.Cancel(r.PathValue("id")) {
		writeErr(w, http.StatusConflict, fmt.Errorf("задание не выполняется или не найдено"))
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "cancelling"})
}

func readJSON(r *http.Request, v any) error {
	body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		return err
	}
	if err := json.Unmarshal(body, v); err != nil {
		return fmt.Errorf("тело запроса не JSON: %w", err)
	}
	return nil
}

var uiTemplate = template.Must(template.New("index").Parse(uiHTML))

func (s *Server) uiIndex(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_ = uiTemplate.Execute(w, map[string]any{
		"Projects":    s.Registry.Projects(),
		"HostVersion": HostVersion,
	})
}

