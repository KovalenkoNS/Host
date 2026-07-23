package host

// uiHTML — встроенная страница Web UI (без CDN и внешних зависимостей).
// Карточка приложения показывает: версию (github — ветка, локальный — из
// README), для локального — ПОСЛЕДНИЙ УКАЗАННЫЙ ПУТЬ, для github —
// исходный репозиторий; строка «Доступность» обновляется живой проверкой
// GET /api/projects/{name}/availability. Недоступный локальный проект
// показывается пунктирной карточкой без кнопок запуска.
//
// ВНИМАНИЕ: это Go raw-строка — внутри НЕЛЬЗЯ использовать обратные кавычки.
const uiHTML = `<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCG Host — приложения</title>
<style>
:root{--ok:#1a7f37;--bad:#b42318;--muted:#68707c}
body{font-family:system-ui,sans-serif;margin:2rem auto;max-width:1180px;padding:0 1rem;background:#f4f6f8;color:#1d2330}
h1{font-size:1.35rem;margin:0} h1 small{color:var(--muted);font-weight:400;font-size:.75em}
h2{font-size:1.02rem;margin:.1rem 0 .3rem;display:flex;align-items:center;gap:.45rem;flex-wrap:wrap}
h3{font-size:1.02rem;margin:1.4rem 0 .5rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;margin-bottom:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:1rem}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:10px;padding:1rem;box-shadow:0 1px 2px rgba(16,24,40,.05)}
.card.off{border-style:dashed;background:#fbfbfa}
.meta{margin:.35rem 0 .55rem;font-size:.82rem}
.meta div{display:flex;gap:.5rem;margin:.18rem 0;align-items:baseline}
.meta .k{color:var(--muted);flex:0 0 8rem}
.meta code{word-break:break-all;background:#f1f3f5;padding:.05rem .35rem;border-radius:4px}
.ok{color:var(--ok)} .bad{color:var(--bad)} .wait{color:var(--muted)}
input{width:100%;box-sizing:border-box;margin:.3rem 0;font-family:monospace;padding:.3rem .4rem;border:1px solid #c6ccd4;border-radius:6px}
button{padding:.35rem .9rem;border:1px solid #8b95a1;border-radius:6px;background:#eef0f3;cursor:pointer}
button:hover{background:#e2e6ea}
button.mini{padding:.1rem .55rem;font-size:.72rem}
button.danger{border-color:#d4a3a3;color:#8f2318}
table{width:100%;border-collapse:collapse;margin-top:1rem;background:#fff}
th,td{border:1px solid #dfe3e8;padding:.4rem .6rem;font-size:.85rem;text-align:left;vertical-align:top}
.running{color:#b8860b}.succeeded{color:var(--ok)}.failed{color:var(--bad)}.cancelled{color:var(--muted)}
.badge{border-radius:6px;padding:.05rem .45rem;font-size:.68rem}
.badge.local{background:#dcfce7;border:1px solid #86efac}
.badge.github{background:#e0e7ff;border:1px solid #a5b4fc}
.forms{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.1rem}
@media(max-width:800px){.forms{grid-template-columns:1fr}}
.form{background:#fff;border:1px dashed #aab3bd;border-radius:10px;padding:.85rem}
.exe{display:flex;gap:.4rem;align-items:center;margin:.25rem 0;flex-wrap:wrap}
.exe code{flex:1 1 70%;background:#f1f3f5;padding:.15rem .35rem;border-radius:4px;font-size:.8rem;word-break:break-all}
pre{white-space:pre-wrap;word-break:break-all;max-height:8rem;overflow:auto;margin:0}
small{color:var(--muted)}
</style></head><body>
<div class="top">
  <h1>SCG Host <small>управление приложениями · v{{.HostVersion}}</small></h1>
  <span><button onclick="rescan()">Обновить список</button> <span id="rescanMsg"></span></span>
</div>

<div class="forms">
  <div class="form">
    <b>Подключить локальный проект</b><br>
    <input id="localDir" placeholder="путь к папке проекта, напр. C:\tools\my-app">
    <button onclick="addLocal()">Подключить</button>
    <span id="localMsg"></span><br>
    <small>Папка используется на месте (не копируется), путь запоминается.
    Версия — из README проекта. Повторное указание пути обновляет привязку.</small>
  </div>
  <div class="form">
    <b>Загрузить проект с GitHub</b><br>
    <input id="ghRepo" placeholder="https://github.com/owner/repo">
    <button onclick="downloadGH()">Загрузить</button>
    <span id="ghMsg"></span><br>
    <small>Весь репозиторий скачивается в папку external-apps. Версия — ветка.
    ⚠ Код исполняется на этой машине — только доверенные проекты.</small>
  </div>
</div>

<h3>Подключённые приложения ({{len .Projects}})</h3>
<div class="grid">
{{range .Projects}}
{{$pname := .Name}}
<div class="card{{if not .Available}} off{{end}}">
  <h2>{{.Name}}
    {{if eq .Source "local"}}<span class="badge local">локальный</span>
    {{else}}<span class="badge github">github</span>{{end}}
    <button class="mini danger" onclick="removeProject('{{.Name}}')">Удалить</button>
  </h2>
  <div class="meta">
    <div><span class="k">Версия</span><b>{{if eq .Source "local"}}v{{.Version}} <small>из README</small>{{else}}{{.Version}} <small>ветка</small>{{end}}</b></div>
    {{if eq .Source "local"}}
    <div><span class="k">Последний путь</span><code>{{.Dir}}</code></div>
    {{else}}
    <div><span class="k">Репозиторий</span><code>{{if .Repo}}github.com/{{.Repo}}{{else}}{{.Origin}}{{end}}</code></div>
    {{end}}
    <div><span class="k">Доступность</span><span class="wait" data-avail data-name="{{.Name}}">проверяю…</span></div>
  </div>
  {{if not .Available}}
    <p class="bad"><small>Папка проекта недоступна. Карточка сохранена с последним
    указанным путём — верните папку на место и нажмите «Обновить список»
    или подключите проект заново.</small></p>
  {{else if .Executables}}
    <small>Исполняемые файлы — запуск по кнопке:</small>
    {{range $exe := .Executables}}
    <div class="exe">
      <code>{{$exe}}</code>
      <button onclick="runProject('{{$pname}}','{{$exe}}')">Запустить</button>
    </div>
    {{end}}
  {{else}}
    <p><small>в проекте не найдено .exe</small></p>
  {{end}}
</div>
{{else}}
<p><small>нет подключённых приложений — подключите локальную папку или загрузите проект с GitHub</small></p>
{{end}}
</div>

<h3>Задания</h3>
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
async function runProject(name,exe){
  const r=await post('/api/projects/'+encodeURIComponent(name)+'/run',{executable:exe});
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
    'подключено: '+(t.loaded.length?t.loaded.join(', '):'—')+
    (t.problems.length?(' | проблемы: '+t.problems.join('; ')):'');
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
// Живая проверка доступности источников: local — папка, github — репозиторий.
async function checkAvail(){
  for(const el of document.querySelectorAll('[data-avail]')){
    try{
      const r=await fetch('/api/projects/'+encodeURIComponent(el.dataset.name)+'/availability');
      const t=await r.json();
      el.textContent=(t.available?'✓ ':'✗ ')+t.detail;
      el.className=t.available?'ok':'bad';
    }catch(e){ el.textContent='✗ проверить не удалось'; el.className='bad'; }
  }
}
refresh(); setInterval(refresh,1000); checkAvail();
</script></body></html>`
