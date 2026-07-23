package host

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

func requireSh(t *testing.T) {
	t.Helper()
	if _, err := exec.LookPath("sh"); err != nil {
		t.Skip("sh недоступен в среде — пропуск интеграционного теста")
	}
}

// makeProject создаёт папку проекта с фейковыми .exe (содержимое "MZ") и,
// если readmeVer != "", README со строкой версии. Возвращает путь.
func makeProject(t *testing.T, root, name, readmeVer string, exes ...string) string {
	t.Helper()
	dir := filepath.Join(root, name)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, e := range exes {
		p := filepath.Join(dir, filepath.FromSlash(e))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte("MZ"), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if readmeVer != "" {
		if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("# "+name+"\n\nВерсия: "+readmeVer+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

func newTestRegistry(t *testing.T) *Registry {
	t.Helper()
	return NewRegistry(filepath.Join(t.TempDir(), "external-apps"), filepath.Join(t.TempDir(), "scg-apps.json"))
}

// ─────────────────────────── launcher ───────────────────────────

func TestLauncherRun(t *testing.T) {
	requireSh(t)
	dir := t.TempDir()
	l := &Launcher{}
	res, err := l.Run(context.Background(), dir, "sh", []string{"-c", "printf out; printf err >&2"}, 0)
	if err != nil {
		t.Fatalf("run: %v", err)
	}
	if res.ExitCode != 0 || res.Stdout != "out" || res.Stderr != "err" {
		t.Fatalf("результат: %+v", res)
	}
	// Ненулевой код выхода — не ошибка запуска, отражается в ExitCode.
	res2, err := l.Run(context.Background(), dir, "sh", []string{"-c", "exit 3"}, 0)
	if err != nil || res2.ExitCode != 3 {
		t.Fatalf("ненулевой код: err=%v exit=%d", err, res2.ExitCode)
	}
	// Несуществующая команда — ошибка запуска.
	if _, err := l.Run(context.Background(), dir, "no-such-command-xyz", nil, 0); err == nil {
		t.Error("несуществующая команда должна давать ошибку запуска")
	}
}

func TestLauncherTimeout(t *testing.T) {
	requireSh(t)
	l := &Launcher{}
	start := time.Now()
	if _, err := l.Run(context.Background(), t.TempDir(), "sh", []string{"-c", "sleep 5"}, 1); err == nil {
		t.Error("ожидалась ошибка таймаута")
	}
	if time.Since(start) > 3*time.Second {
		t.Errorf("таймаут (1с) не сработал вовремя: %s", time.Since(start))
	}
}

func TestLauncherCancel(t *testing.T) {
	requireSh(t)
	l := &Launcher{}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		_, err := l.Run(ctx, t.TempDir(), "sh", []string{"-c", "sleep 30"}, 60)
		done <- err
	}()
	time.Sleep(150 * time.Millisecond)
	cancel()
	select {
	case err := <-done:
		if err == nil {
			t.Error("после отмены ожидалась ошибка")
		}
	case <-time.After(3 * time.Second):
		t.Fatal("отмена не завершила запуск вовремя (WaitDelay?)")
	}
}

func TestResolveCommand(t *testing.T) {
	dir := t.TempDir()
	exe := filepath.Join(dir, "app.exe")
	os.WriteFile(exe, []byte("MZ"), 0o755)
	if got := resolveCommand(dir, "app.exe"); got != exe {
		t.Errorf("resolveCommand(app.exe)=%q, ожидалось %q", got, exe)
	}
	if got := resolveCommand(dir, "python3"); got != "python3" {
		t.Errorf("resolveCommand(python3)=%q, ожидался поиск в PATH", got)
	}
	if got := resolveCommand(dir, "bin/app.exe"); got != filepath.Join(dir, "bin", "app.exe") {
		t.Errorf("resolveCommand(bin/app.exe)=%q", got)
	}
}

// ─────────────────────────── readme ───────────────────────────

func TestReadmeVersion(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "README.md"), []byte("# Тул\n\nВерсия: 1.2.3\n"), 0o644)
	if v, ok := readmeVersion(d); !ok || v != "1.2.3" {
		t.Errorf("readmeVersion=%q ok=%v, ожидалось 1.2.3", v, ok)
	}
	d2 := t.TempDir()
	os.WriteFile(filepath.Join(d2, "readme.txt"), []byte("hello v0.9 release"), 0o644)
	if v, ok := readmeVersion(d2); !ok || v != "0.9" {
		t.Errorf("readmeVersion(txt)=%q ok=%v, ожидалось 0.9", v, ok)
	}
	if _, ok := readmeVersion(t.TempDir()); ok {
		t.Error("без README должно быть ok=false")
	}
}

// ─────────────────────────── registry: локальные ───────────────────────────

func TestRegistryLocalProject(t *testing.T) {
	src := makeProject(t, t.TempDir(), "my-app", "1.4.0", "app.exe", "bin/tool.exe")
	reg := newTestRegistry(t)
	p, err := reg.AddLocalProject(src)
	if err != nil {
		t.Fatalf("add-local: %v", err)
	}
	if p.Name != "my-app" || p.Source != SourceLocal || p.Version != "1.4.0" {
		t.Fatalf("проект: %+v", p)
	}
	if len(p.Executables) != 2 || p.Executables[0] != "app.exe" || p.Executables[1] != "bin/tool.exe" {
		t.Fatalf("список exe: %v", p.Executables)
	}
	if got, ok := reg.GetProject("my-app"); !ok || got.Source != SourceLocal {
		t.Fatalf("get: %+v ok=%v", got, ok)
	}
	if len(reg.Projects()) != 1 {
		t.Fatalf("projects: %d", len(reg.Projects()))
	}
	// Отключение локального проекта не удаляет его папку на диске.
	if err := reg.RemoveProject("my-app"); err != nil {
		t.Fatal(err)
	}
	if _, ok := reg.GetProject("my-app"); ok {
		t.Error("проект должен быть отключён")
	}
	if _, err := os.Stat(filepath.Join(src, "app.exe")); err != nil {
		t.Error("исходная папка локального проекта не должна удаляться")
	}
}

func TestRegistryLoadStatePersist(t *testing.T) {
	src := makeProject(t, t.TempDir(), "keep-me", "2.0", "run.exe")
	ext := filepath.Join(t.TempDir(), "external-apps")
	state := filepath.Join(t.TempDir(), "scg-apps.json")

	reg1 := NewRegistry(ext, state)
	if _, err := reg1.AddLocalProject(src); err != nil {
		t.Fatal(err)
	}
	// Новый реестр с тем же файлом состояния восстанавливает локальный проект.
	reg2 := NewRegistry(ext, state)
	reg2.LoadState()
	loaded, problems := reg2.Rescan()
	if len(problems) != 0 || len(loaded) != 1 || loaded[0] != "keep-me" {
		t.Fatalf("восстановление: loaded=%v problems=%v", loaded, problems)
	}
	if p, ok := reg2.GetProject("keep-me"); !ok || !p.Available {
		t.Fatalf("keep-me не восстановлен из состояния: %+v ok=%v", p, ok)
	}
	// Исчезновение папки НЕ удаляет карточку: она сохраняется с последним
	// указанным путём (Available=false), с предупреждением, а не падением.
	os.RemoveAll(src)
	loaded, problems = reg2.Rescan()
	if len(loaded) != 0 || len(problems) != 1 {
		t.Fatalf("после удаления папки: loaded=%v problems=%v", loaded, problems)
	}
	p, ok := reg2.GetProject("keep-me")
	if !ok || p.Available || p.Dir != src {
		t.Fatalf("карточка с последним путём должна сохраниться: %+v ok=%v", p, ok)
	}
	if len(p.Executables) != 0 {
		t.Errorf("у недоступного проекта не должно быть exe: %v", p.Executables)
	}
	// И после ПЕРЕЗАПУСКА (новый реестр из того же файла состояния) карточка
	// по-прежнему видна с последним указанным путём и последней версией.
	reg3 := NewRegistry(ext, state)
	reg3.LoadState()
	reg3.Rescan()
	p3, ok := reg3.GetProject("keep-me")
	if !ok || p3.Available || p3.Dir != src {
		t.Fatalf("после перезапуска: %+v ok=%v", p3, ok)
	}
	if p3.Version != "2.0" {
		t.Errorf("последняя известная версия должна сохраняться: %q", p3.Version)
	}
}

func TestAddLocalRepointUpdatesPath(t *testing.T) {
	rootA, rootB := t.TempDir(), t.TempDir()
	a := makeProject(t, rootA, "same-app", "1.0", "a.exe")
	b := makeProject(t, rootB, "same-app", "2.0", "b.exe")
	reg := newTestRegistry(t)
	if _, err := reg.AddLocalProject(a); err != nil {
		t.Fatal(err)
	}
	// Повторное указание того же имени с другим путём — переподключение:
	// побеждает ПОСЛЕДНИЙ указанный путь.
	p, err := reg.AddLocalProject(b)
	if err != nil {
		t.Fatalf("re-point должен обновлять путь: %v", err)
	}
	if p.Dir != b || p.Version != "2.0" {
		t.Fatalf("ожидался последний путь %s: %+v", b, p)
	}
	if got, _ := reg.GetProject("same-app"); got.Dir != b {
		t.Fatalf("в реестре не последний путь: %+v", got)
	}
}

func TestStartProjectUnavailableRejected(t *testing.T) {
	src := makeProject(t, t.TempDir(), "gone-app", "", "run.exe")
	reg := newTestRegistry(t)
	if _, err := reg.AddLocalProject(src); err != nil {
		t.Fatal(err)
	}
	os.RemoveAll(src)
	reg.Rescan()
	jm := NewJobManager(reg, &Launcher{}, 0)
	if _, err := jm.StartProject("gone-app", "run.exe", nil); err == nil {
		t.Fatal("запуск из недоступной папки должен отвергаться")
	} else if !strings.Contains(err.Error(), "недоступна") {
		t.Errorf("ошибка должна объяснять причину: %v", err)
	}
}

// ─────────────────────────── github ───────────────────────────

func TestParseGitHubRepo(t *testing.T) {
	cases := []struct {
		in, owner, name string
		ok              bool
	}{
		{"anthropics/claude-code", "anthropics", "claude-code", true},
		{"https://github.com/Owner/Repo.git", "Owner", "Repo", true},
		{"git@github.com:o/r.git", "o", "r", true},
		{"", "", "", false},
		{"justname", "", "", false},
		{"a/b/c", "", "", false},
		{"bad name/repo", "", "", false},
	}
	for _, c := range cases {
		o, n, err := ParseGitHubRepo(c.in)
		if c.ok && (err != nil || o != c.owner || n != c.name) {
			t.Errorf("%q → %q/%q, %v", c.in, o, n, err)
		}
		if !c.ok && err == nil {
			t.Errorf("%q: ожидалась ошибка", c.in)
		}
	}
}

// makeRepoZip — архив в формате GitHub: всё под корнем repo-ref/.
func makeRepoZip(t *testing.T, root string, files map[string]string) []byte {
	t.Helper()
	var buf bytes.Buffer
	zw := zip.NewWriter(&buf)
	for name, content := range files {
		w, err := zw.CreateHeader(&zip.FileHeader{Name: root + "/" + name, Method: zip.Deflate})
		if err != nil {
			t.Fatal(err)
		}
		w.Write([]byte(content))
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	return buf.Bytes()
}

func githubStub(t *testing.T, path string, zipData []byte) func() {
	t.Helper()
	stub := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == path {
			w.Write(zipData)
			return
		}
		http.NotFound(w, r)
	}))
	old := codeloadBase
	codeloadBase = stub.URL
	return func() { codeloadBase = old; stub.Close() }
}

func TestDownloadProjectViaStub(t *testing.T) {
	zipData := makeRepoZip(t, "Tool-main", map[string]string{
		"readme.md":     "проект",
		"App.exe":       "MZ",
		"tools/aux.exe": "MZ",
		"data/conf.ini": "x=1",
	})
	defer githubStub(t, "/acme/Tool/zip/refs/heads/main", zipData)()

	ext := t.TempDir()
	p, err := DownloadProject("https://github.com/acme/Tool", ext)
	if err != nil {
		t.Fatalf("download: %v", err)
	}
	if p.Name != "tool" || p.Source != SourceGitHub || p.Version != "main" || p.Origin != "github:acme/Tool@main" {
		t.Fatalf("проект: %+v", p)
	}
	if len(p.Executables) != 2 || p.Executables[0] != "App.exe" || p.Executables[1] != "tools/aux.exe" {
		t.Fatalf("список exe: %v", p.Executables)
	}
	for _, f := range []string{projectMetaFile, "App.exe", filepath.Join("data", "conf.ini")} {
		if _, err := os.Stat(filepath.Join(ext, "acme-Tool", f)); err != nil {
			t.Errorf("нет файла %s: %v", f, err)
		}
	}
	reg := NewRegistry(ext, filepath.Join(t.TempDir(), "scg-apps.json"))
	loaded, problems := reg.Rescan()
	if len(problems) != 0 || len(loaded) != 1 || loaded[0] != "tool" {
		t.Fatalf("rescan: loaded=%v problems=%v", loaded, problems)
	}
	// Повторная загрузка обновляет без дублей.
	if _, err := DownloadProject("acme/Tool", ext); err != nil {
		t.Fatalf("повторная загрузка: %v", err)
	}
	if loaded, _ := reg.Rescan(); len(loaded) != 1 {
		t.Fatalf("после повторной загрузки: %v", loaded)
	}
}

func TestDownloadProjectNoExe(t *testing.T) {
	zipData := makeRepoZip(t, "noexe-main", map[string]string{"main.py": "print(1)"})
	defer githubStub(t, "/acme/noexe/zip/refs/heads/main", zipData)()

	ext := t.TempDir()
	p, err := DownloadProject("acme/noexe", ext)
	if err != nil {
		t.Fatalf("проект без .exe не должен быть ошибкой: %v", err)
	}
	if len(p.Executables) != 0 {
		t.Errorf("ожидался пустой список exe: %v", p.Executables)
	}
	if _, err := os.Stat(filepath.Join(ext, "acme-noexe", "main.py")); err != nil {
		t.Errorf("проект должен сохраняться: %v", err)
	}
}

func TestScanExternalRootProjects(t *testing.T) {
	ext := t.TempDir()
	makeProject(t, ext, "my-tool", "", "root.exe", "bin/tool.exe")
	os.MkdirAll(filepath.Join(ext, "docs-only"), 0o755)
	os.WriteFile(filepath.Join(ext, "docs-only", "readme.md"), []byte("x"), 0o644)
	os.WriteFile(filepath.Join(ext, "loose.exe"), []byte("MZ"), 0o755) // файл в корне — не проект

	reg := NewRegistry(ext, "")
	loaded, problems := reg.Rescan()
	if len(problems) != 0 || len(loaded) != 2 {
		t.Fatalf("loaded=%v problems=%v", loaded, problems)
	}
	mt, ok := reg.GetProject("my-tool")
	if !ok || mt.Source != SourceGitHub || len(mt.Executables) != 2 ||
		mt.Executables[0] != "root.exe" || mt.Executables[1] != "bin/tool.exe" {
		t.Fatalf("my-tool: %+v ok=%v", mt, ok)
	}
	if do, ok := reg.GetProject("docs-only"); !ok || len(do.Executables) != 0 {
		t.Fatalf("docs-only без exe: %+v ok=%v", do, ok)
	}
}

func TestFindAllExesDeterministic(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, "z"), 0o755)
	os.WriteFile(filepath.Join(dir, "z", "a.exe"), []byte("MZ"), 0o755)
	os.WriteFile(filepath.Join(dir, "b.exe"), []byte("MZ"), 0o755)
	os.WriteFile(filepath.Join(dir, "a.exe"), []byte("MZ"), 0o755)
	got := findAllExes(dir)
	want := []string{"a.exe", "b.exe", "z/a.exe"}
	if len(got) != len(want) {
		t.Fatalf("findAllExes=%v, ожидалось %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("findAllExes=%v, ожидалось %v", got, want)
		}
	}
	if len(findAllExes(t.TempDir())) != 0 {
		t.Error("пустая папка → пустой список")
	}
}

func TestCheckRepoAvailability(t *testing.T) {
	zipData := makeRepoZip(t, "Live-main", map[string]string{"app.exe": "MZ"})
	defer githubStub(t, "/acme/Live/zip/refs/heads/main", zipData)()

	// Существующая ветка → доступен.
	if ok, detail := CheckRepoAvailability("acme/Live", "main"); !ok {
		t.Errorf("репозиторий должен быть доступен: %s", detail)
	}
	// Несуществующий репозиторий → недоступен, с причиной.
	if ok, detail := CheckRepoAvailability("acme/Ghost", "main"); ok || detail == "" {
		t.Errorf("несуществующий репозиторий: ok=%v detail=%q", ok, detail)
	}
	// Пустая ветка → перебор main/master.
	if ok, _ := CheckRepoAvailability("acme/Live", ""); !ok {
		t.Error("перебор main/master должен найти main")
	}
	// Кривая ссылка → ошибка разбора.
	if ok, _ := CheckRepoAvailability("не ссылка", ""); ok {
		t.Error("мусор на входе не должен быть доступен")
	}
}

func TestRepoFromOrigin(t *testing.T) {
	if r, b := repoFromOrigin("github:acme/Tool@main"); r != "acme/Tool" || b != "main" {
		t.Errorf("repoFromOrigin=%q,%q", r, b)
	}
	if r, _ := repoFromOrigin("C:\\some\\dir"); r != "" {
		t.Errorf("не-github origin: %q", r)
	}
}

func TestServerAvailabilityEndpoint(t *testing.T) {
	zipData := makeRepoZip(t, "Repo-main", map[string]string{"app.exe": "MZ"})
	defer githubStub(t, "/o/Repo/zip/refs/heads/main", zipData)()

	ext := filepath.Join(t.TempDir(), "external-apps")
	src := makeProject(t, t.TempDir(), "loc-app", "1.0", "run.exe")
	reg := NewRegistry(ext, filepath.Join(t.TempDir(), "scg-apps.json"))
	if _, err := reg.AddLocalProject(src); err != nil {
		t.Fatal(err)
	}
	if _, err := DownloadProject("o/Repo", ext); err != nil {
		t.Fatal(err)
	}
	reg.Rescan()
	srv := httptest.NewServer((&Server{Registry: reg, Jobs: NewJobManager(reg, &Launcher{}, 0)}).Handler())
	defer srv.Close()

	check := func(name string) (ok bool, detail string) {
		t.Helper()
		resp, err := http.Get(srv.URL + "/api/projects/" + name + "/availability")
		if err != nil {
			t.Fatal(err)
		}
		defer resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			t.Fatalf("%s: код %d", name, resp.StatusCode)
		}
		var out struct {
			Available bool   `json:"available"`
			Detail    string `json:"detail"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
			t.Fatal(err)
		}
		return out.Available, out.Detail
	}

	if ok, d := check("loc-app"); !ok {
		t.Errorf("локальный проект должен быть доступен: %s", d)
	}
	if ok, d := check("repo"); !ok {
		t.Errorf("github-проект должен быть доступен через стаб: %s", d)
	}
	// Папка локального проекта исчезла → живая проверка это видит.
	os.RemoveAll(src)
	if ok, d := check("loc-app"); ok || !strings.Contains(d, src) {
		t.Errorf("должна показываться недоступность с последним путём: ok=%v %q", ok, d)
	}
	// Неизвестный проект → 404.
	resp, err := http.Get(srv.URL + "/api/projects/ghost/availability")
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("ghost: код %d, ожидался 404", resp.StatusCode)
	}
}

func TestExtractRepoZipSlip(t *testing.T) {
	var buf bytes.Buffer
	zw := zip.NewWriter(&buf)
	w, _ := zw.Create("repo-main/../../evil.txt")
	w.Write([]byte("zip-slip"))
	zw.Close()
	if err := extractRepoZip(buf.Bytes(), t.TempDir()); err == nil {
		t.Fatal("zip-slip должен отвергаться")
	}
}

// ─────────────────────────── jobs ───────────────────────────

func TestStartProjectValidates(t *testing.T) {
	ext := t.TempDir()
	makeProject(t, ext, "demo", "", "tool.exe")
	reg := NewRegistry(ext, "")
	reg.Rescan()
	jm := NewJobManager(reg, &Launcher{}, 0)

	if _, err := jm.StartProject("demo", "../evil.exe", nil); err == nil {
		t.Error("exe вне списка должен отвергаться")
	}
	if _, err := jm.StartProject("ghost", "tool.exe", nil); err == nil {
		t.Error("несуществующий проект должен отвергаться")
	}
	// Валидный выбор: задание создаётся; фейковый .exe не запустится —
	// задание завершится ошибкой асинхронно, но выбор/валидация проходят.
	job, err := jm.StartProject("demo", "tool.exe", nil)
	if err != nil {
		t.Fatalf("валидный exe: %v", err)
	}
	done, err := jm.Wait(job.ID, 5*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	if done.State == JobRunning {
		t.Error("задание должно завершиться")
	}
	if done.Executable != "tool.exe" {
		t.Errorf("executable=%q, ожидался tool.exe", done.Executable)
	}
}

func TestJobsParallelList(t *testing.T) {
	ext := t.TempDir()
	makeProject(t, ext, "fast", "", "a.exe")
	reg := NewRegistry(ext, "")
	reg.Rescan()
	jm := NewJobManager(reg, &Launcher{}, 0)

	var wg sync.WaitGroup
	for i := 0; i < 5; i++ {
		job, err := jm.StartProject("fast", "a.exe", nil)
		if err != nil {
			t.Fatal(err)
		}
		wg.Add(1)
		go func(id string) {
			defer wg.Done()
			if _, err := jm.Wait(id, 10*time.Second); err != nil {
				t.Errorf("wait %s: %v", id, err)
			}
		}(job.ID)
	}
	wg.Wait()
	if len(jm.List()) != 5 {
		t.Errorf("list: %d заданий, ожидалось 5", len(jm.List()))
	}
	// Отмена уже завершённого задания не принимается.
	for _, j := range jm.List() {
		if jm.Cancel(j.ID) {
			t.Errorf("cancel завершённого задания %s должен вернуть false", j.ID)
		}
	}
}

// ─────────────────────────── персистентность ───────────────────────────

func TestPersistStateBothSources(t *testing.T) {
	src := makeProject(t, t.TempDir(), "local-app", "3.1", "run.exe")
	zipData := makeRepoZip(t, "Repo-main", map[string]string{"app.exe": "MZ"})
	defer githubStub(t, "/o/Repo/zip/refs/heads/main", zipData)()

	ext := filepath.Join(t.TempDir(), "external-apps")
	state := filepath.Join(t.TempDir(), "scg-apps.json")
	reg := NewRegistry(ext, state)
	if _, err := reg.AddLocalProject(src); err != nil {
		t.Fatal(err)
	}
	if _, err := DownloadProject("o/Repo", ext); err != nil {
		t.Fatal(err)
	}
	reg.Rescan()

	var st stateFile
	raw, err := os.ReadFile(state)
	if err != nil {
		t.Fatalf("нет файла состояния: %v", err)
	}
	json.Unmarshal(raw, &st)
	if len(st.Local) != 1 || st.Local[0].Name != "local-app" || st.Local[0].Version != "3.1" {
		t.Fatalf("local: %+v", st.Local)
	}
	if len(st.External) != 1 || st.External[0].Name != "repo" {
		t.Fatalf("external: %+v", st.External)
	}
	// Автообновление: удаление github-проекта переписывает состояние.
	if err := reg.RemoveProject("repo"); err != nil {
		t.Fatal(err)
	}
	raw, _ = os.ReadFile(state)
	var st2 stateFile
	json.Unmarshal(raw, &st2)
	if len(st2.External) != 0 || len(st2.Local) != 1 {
		t.Errorf("после удаления github: local=%d external=%d", len(st2.Local), len(st2.External))
	}
}

// ─────────────────────────── listen / имена ───────────────────────────

func TestListenSmartPicksNextFreePort(t *testing.T) {
	busy, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer busy.Close()
	port := busy.Addr().(*net.TCPAddr).Port
	ln, page, err := ListenSmart(net.JoinHostPort("127.0.0.1", strconv.Itoa(port)))
	if err != nil {
		t.Fatalf("ListenSmart при занятом порте: %v", err)
	}
	defer ln.Close()
	got := PortOf(ln)
	if got == port || got == 0 {
		t.Fatalf("должен быть выбран другой порт, получен %d (занят %d)", got, port)
	}
	if !strings.Contains(page, strconv.Itoa(got)) {
		t.Errorf("URL %q не содержит порт %d", page, got)
	}
}

func TestComponentNameFor(t *testing.T) {
	if got := componentNameFor("", "My.Repo_X"); got != "my.repo_x" {
		t.Errorf("componentNameFor(My.Repo_X)=%q", got)
	}
	if got := componentNameFor("", "___"); got != "external-project" {
		t.Errorf("componentNameFor(___)=%q, ожидалось external-project", got)
	}
	if got := componentNameFor("GOOD-name", "r"); got != "good-name" {
		t.Errorf("componentNameFor(GOOD-name)=%q", got)
	}
}
