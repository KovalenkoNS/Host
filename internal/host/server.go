package host

import (
	"encoding/json"
	"fmt"
	"html/template"
	"io"
	"net/http"
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

type runProjectBody struct {
	Executable string   `json:"executable"`
	Args       []string `json:"args,omitempty"`
}

func (s *Server) apiProjectRun(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	var in runProjectBody
	if err := readJSON(r, &in); err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	job, err := s.Jobs.StartProject(name, in.Executable, in.Args)
	if err != nil {
		writeErr(w, http.StatusBadRequest, err)
		return
	}
	writeJSON(w, http.StatusAccepted, job)
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
	_ = uiTemplate.Execute(w, map[string]any{"Projects": s.Registry.Projects()})
}

// uiHTML — встроенная страница. Проекты из двух источников (локальные и
// GitHub) показаны карточками со списком .exe: у каждого своя кнопка запуска.
// Таблица заданий обновляется опросом /api/jobs.
const uiHTML = `<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>SCG Host — приложения</title>
<style>
body{font-family:system-ui,sans-serif;margin:2rem;background:#f7f7f5;color:#222}
h1{font-size:1.3rem} h2{font-size:1.05rem;margin:.2rem 0} h3{font-size:1.05rem;margin:1.4rem 0 .4rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1rem}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem}
.card small{color:#666}
input{width:100%;box-sizing:border-box;margin:.3rem 0;font-family:monospace}
button{padding:.35rem .9rem;border:1px solid #888;border-radius:6px;background:#eee;cursor:pointer}
button:hover{background:#e2e2e2}
table{width:100%;border-collapse:collapse;margin-top:1rem;background:#fff}
th,td{border:1px solid #ddd;padding:.4rem .6rem;font-size:.85rem;text-align:left;vertical-align:top}
.running{color:#b8860b}.succeeded{color:#1a7f37}.failed{color:#b42318}.cancelled{color:#666}
.badge{border-radius:6px;padding:0 .4rem;font-size:.7rem;vertical-align:middle}
.local{background:#dcfce7;border:1px solid #86efac}.github{background:#e0e7ff;border:1px solid #a5b4fc}
.mini{padding:.1rem .5rem;font-size:.7rem}
.forms{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}
.form{background:#fff;border:1px dashed #aaa;border-radius:8px;padding:.8rem}
.exe{display:flex;gap:.4rem;align-items:center;margin:.25rem 0;flex-wrap:wrap}
.exe code{flex:1 1 55%;background:#f2f2f0;padding:.15rem .35rem;border-radius:4px;font-size:.8rem;word-break:break-all}
.exe input{flex:1 1 30%;width:auto;margin:0}
pre{white-space:pre-wrap;word-break:break-all;max-height:8rem;overflow:auto;margin:0}
</style></head><body>
<h1>SCG Host — управление приложениями</h1>
<p><button onclick="rescan()">Обновить список</button> <span id="rescanMsg"></span></p>

<div class="forms">
  <div class="form">
    <b>Подключить локальный проект</b><br>
    <input id="localDir" placeholder="путь к папке проекта, напр. C:\tools\my-app">
    <button onclick="addLocal()">Подключить</button>
    <span id="localMsg"></span><br>
    <small>Папка используется на месте (не копируется). Хост покажет список
    её .exe. Версия берётся из README проекта.</small>
  </div>
  <div class="form">
    <b>Загрузить проект с GitHub</b><br>
    <input id="ghRepo" placeholder="https://github.com/owner/repo">
    <button onclick="downloadGH()">Загрузить</button>
    <span id="ghMsg"></span><br>
    <small>Весь проект скачивается в external-apps. Версия — ветка репозитория.
    ⚠ Код исполняется на этой машине — только доверенные проекты.</small>
  </div>
</div>

<h3>Подключённые проекты ({{len .Projects}})</h3>
<div class="grid">
{{range .Projects}}
{{$pname := .Name}}
<div class="card">
  <h2>{{.Name}}
    {{if eq .Source "local"}}<span class="badge local">локальный</span> <small>v{{.Version}}</small>
    {{else}}<span class="badge github">github</span> <small>ветка {{.Version}}</small>{{end}}
    <button class="mini" onclick="removeProject('{{.Name}}')">Удалить</button>
  </h2>
  <small>{{.Description}}</small>
  {{if .Executables}}
    <p><small>Исполняемые файлы — выберите и запустите:</small></p>
    {{range $i, $exe := .Executables}}
    <div class="exe">
      <code>{{$exe}}</code>
      <input id="pargs-{{$pname}}-{{$i}}" placeholder="аргументы">
      <button onclick="runProject('{{$pname}}','{{$exe}}','pargs-{{$pname}}-{{$i}}')">Запустить</button>
    </div>
    {{end}}
  {{else}}
    <p><small>в проекте не найдено .exe</small></p>
  {{end}}
</div>
{{else}}
<p><small>нет подключённых проектов — подключите локальную папку или загрузите с GitHub</small></p>
{{end}}
</div>

<table><thead><tr>
<th>Задание</th><th>Проект</th><th>Файл</th><th>Статус</th><th>мс</th><th>Результат / ошибка</th><th></th>
</tr></thead><tbody id="jobs"></tbody></table>
<script>
async function post(url,body){
  return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
    body:body?JSON.stringify(body):null});
}
async function addLocal(){
  const dir=document.getElementById('localDir').value.trim();
  if(!dir){ alert('Укажите путь к папке'); return; }
  const r=await post('/api/projects/local',{dir:dir}); const t=await r.json();
  if(!r.ok){ document.getElementById('localMsg').textContent=' ✗ '+(t.error||r.statusText); return; }
  document.getElementById('localMsg').textContent=' ✓ '+t.name+' (.exe: '+(t.executables?t.executables.length:0)+')';
  setTimeout(()=>location.reload(),700);
}
async function downloadGH(){
  const repo=document.getElementById('ghRepo').value.trim();
  if(!repo){ alert('Вставьте ссылку на репозиторий'); return; }
  const msg=document.getElementById('ghMsg'); msg.textContent=' … скачиваю, подождите';
  const r=await post('/api/projects/github',{repo:repo}); const t=await r.json();
  if(!r.ok){ msg.textContent=' ✗ '+(t.error||r.statusText); return; }
  msg.textContent=' ✓ '+t.name+' (.exe: '+(t.executables?t.executables.length:0)+')';
  setTimeout(()=>location.reload(),900);
}
async function runProject(name,exe,argsId){
  let args=null;
  const raw=(document.getElementById(argsId).value||'').trim();
  if(raw){ args=raw.split(/\s+/); }
  const r=await post('/api/projects/'+encodeURIComponent(name)+'/run',{executable:exe,args:args});
  if(!r.ok){ const t=await r.json(); alert(t.error||r.statusText); }
  refresh();
}
async function removeProject(name){
  if(!confirm('Отключить проект '+name+'?')) return;
  const r=await post('/api/projects/'+encodeURIComponent(name)+'/remove');
  if(!r.ok){ const t=await r.json(); alert(t.error||r.statusText); return; }
  location.reload();
}
async function cancelJob(id){ await post('/api/jobs/'+id+'/cancel'); refresh(); }
async function rescan(){
  const r=await post('/api/projects/rescan'); const t=await r.json();
  document.getElementById('rescanMsg').textContent=
    'подключено: '+t.loaded.join(', ')+(t.problems.length?(' | проблемы: '+t.problems.join('; ')):'');
  setTimeout(()=>location.reload(),800);
}
async function refresh(){
  const r=await fetch('/api/jobs'); const jobs=await r.json();
  const tb=document.getElementById('jobs'); tb.innerHTML='';
  for(const j of jobs){
    const tr=document.createElement('tr');
    const out=j.error?j.error:(j.result?JSON.stringify(j.result):'');
    tr.innerHTML='<td><code>'+j.id.slice(0,8)+'</code></td><td>'+j.project+'</td><td>'+j.executable+
      '</td><td class="'+j.state+'">'+j.state+'</td><td>'+(j.duration_ms||'')+
      '</td><td><pre></pre></td><td>'+(j.state==='running'?'<button onclick="cancelJob(\''+j.id+'\')">Отменить</button>':'')+'</td>';
    tr.querySelector('pre').textContent=out;
    tb.appendChild(tr);
  }
}
refresh(); setInterval(refresh,1000);
</script></body></html>`
