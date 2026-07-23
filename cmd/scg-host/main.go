// Команда scg-host — УПРАВЛЯЮЩЕЕ ПРИЛОЖЕНИЕ SCG.
//
// Назначение и жёсткая граница ответственности:
//
//	Это приложение занимается ИСКЛЮЧИТЕЛЬНО запуском приложений и показом их
//	результатов. Здесь нет предметной логики.
//
// Приложение = ПРОЕКТ (папка с исполняемыми файлами), подключаемый из одного
// из двух источников:
//   - ЛОКАЛЬНЫЙ: путь к папке на машине пользователя (используется на месте);
//   - GITHUB: публичный репозиторий, скачиваемый целиком в external-apps/.
//
// Пользователь выбирает нужный .exe из проекта и запускает его как есть (raw):
// каждый запуск — отдельный процесс ОС с минимальным окружением.
//
// Интерфейсы для человека:
//   - запуск БЕЗ АРГУМЕНТОВ (в т.ч. двойным щелчком) — локальный старт
//     сервера с автооткрытием браузера;
//   - CLI: projects | add-local | download | run-project | serve;
//   - Web UI + HTTP API (serve): подключение проектов, выбор .exe, запуск,
//     параллельные задания, отмена.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"time"

	"scg-host/internal/host"
)

// ─────────────────────────────────────────────────────────────────────────
// СЕКЦИЯ 1. Точка входа и разбор подкоманд.
// ─────────────────────────────────────────────────────────────────────────

func main() {
	if len(os.Args) < 2 {
		if err := launchLocal(); err != nil {
			fmt.Fprintln(os.Stderr, "ошибка:", err)
			waitEnterOnWindows()
			os.Exit(1)
		}
		return
	}
	var err error
	switch os.Args[1] {
	case "projects":
		err = cmdProjects(os.Args[2:])
	case "add-local":
		err = cmdAddLocal(os.Args[2:])
	case "download":
		err = cmdDownload(os.Args[2:])
	case "run-project":
		err = cmdRunProject(os.Args[2:])
	case "serve":
		err = cmdServe(os.Args[2:])
	case "help", "-h", "--help":
		usage()
	default:
		fmt.Fprintf(os.Stderr, "неизвестная подкоманда %q\n", os.Args[1])
		usage()
		os.Exit(2)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "ошибка:", err)
		os.Exit(1)
	}
}

func usage() {
	fmt.Fprintf(os.Stderr, "scg-host v%s\n", host.HostVersion)
	fmt.Fprint(os.Stderr, `scg-host — управляющее приложение SCG (только запуск приложений)

Запуск без аргументов — локальный старт с автооткрытием браузера.

Приложение = проект (папка с .exe) из двух источников: локальный путь
и загрузка с GitHub (папка external-apps/).

Подкоманды:
  projects [--dir DIR] [--format table|json]
                    список подключённых проектов и их .exe
  add-local <путь к папке> [--dir DIR]
                    подключить локальный проект (используется на месте)
  download <ссылка на репозиторий> [--dir DIR]
                    скачать ВЕСЬ проект с GitHub в external-apps (нужен интернет)
  run-project <проект> <exe> [--dir DIR] [--timeout]
                    запустить выбранный .exe из проекта (как есть, без аргументов)
  serve [--dir DIR] [--addr :8080] [--max-parallel 0] [--open]
                    Web UI + HTTP API

--dir — рабочий каталог (по умолчанию рядом с исполняемым файлом): здесь
создаются external-apps/ и scg-apps.json (сводка подключённых проектов).
`)
}

// ─────────────────────────────────────────────────────────────────────────
// СЕКЦИЯ 2. Запуск без аргументов — локальный старт.
//
// Хост стартует на этой машине, браузер по умолчанию открывается
// автоматически. Если scg-host уже запущен (повторный двойной щелчок),
// новый экземпляр не поднимается — открывается страница существующего.
// Занятый порт → следующий свободный (см. ListenSmart).
// ─────────────────────────────────────────────────────────────────────────

func launchLocal() error {
	fmt.Println("scg-host v" + host.HostVersion + " — управляющее приложение SCG")
	fmt.Println()
	const preferred = "http://localhost:8080"
	if n, err := probeLocal(preferred, 700*time.Millisecond); err == nil {
		fmt.Printf("scg-host уже запущен (%s, проектов: %d) — открываю его страницу.\n", preferred, n)
		openBrowser(preferred)
		fmt.Println("Это окно можно закрыть: работает ранее запущенный экземпляр.")
		waitEnterOnWindows()
		return nil
	}
	fmt.Println("Локальный запуск. Откроется браузер.")
	fmt.Println("Не закрывайте это окно, пока работаете. Остановка — Ctrl+C.")
	return serveOn("", ":8080", 0, true)
}

// probeLocal проверяет, не запущен ли УЖЕ локальный экземпляр scg-host
// (только localhost — self-detection). Возвращает число проектов.
func probeLocal(base string, timeout time.Duration) (int, error) {
	client := &http.Client{Timeout: timeout}
	resp, err := client.Get(base + "/api/projects")
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("по адресу %s ответ с кодом %d", base, resp.StatusCode)
	}
	var list []json.RawMessage
	if err := json.NewDecoder(resp.Body).Decode(&list); err != nil {
		return 0, err
	}
	return len(list), nil
}

// openBrowser открывает страницу в браузере ПО УМОЛЧАНИЮ текущей ОС.
func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default: // linux и прочие
		cmd = exec.Command("xdg-open", url)
	}
	if err := cmd.Start(); err != nil {
		fmt.Fprintln(os.Stderr, "не удалось открыть браузер автоматически — откройте вручную:", url)
	}
}

// waitEnterOnWindows не даёт окну консоли закрыться мгновенно при запуске
// двойным щелчком (актуально для Windows).
func waitEnterOnWindows() {
	if runtime.GOOS != "windows" {
		return
	}
	fmt.Print("Нажмите Enter для выхода...")
	_, _ = bufio.NewReader(os.Stdin).ReadString('\n')
}

// ─────────────────────────────────────────────────────────────────────────
// СЕКЦИЯ 3. Инициализация реестра проектов.
// ─────────────────────────────────────────────────────────────────────────

// resolveBaseDir — рабочий каталог хоста. По умолчанию (пустой dir) — каталог
// исполняемого файла: тогда external-apps/ и scg-apps.json всегда лежат рядом
// с exe, независимо от текущего каталога (важно для запуска двойным щелчком).
func resolveBaseDir(dir string) (string, error) {
	if dir != "" {
		return filepath.Abs(dir)
	}
	if exe, err := os.Executable(); err == nil {
		return filepath.Dir(exe), nil
	}
	return filepath.Abs(".")
}

// openStore инициализирует реестр: external-apps/ и scg-apps.json в рабочем
// каталоге, восстанавливает локальные проекты из состояния и сканирует.
func openStore(dir string) (*host.Registry, error) {
	base, err := resolveBaseDir(dir)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(base, 0o755); err != nil {
		return nil, fmt.Errorf("не удалось создать рабочий каталог %s: %w", base, err)
	}
	extRoot := filepath.Join(base, host.ExternalAppsDirName)
	statePath := filepath.Join(base, "scg-apps.json")
	reg := host.NewRegistry(extRoot, statePath)
	reg.LoadState() // восстановить локальные проекты (их пути)
	loaded, problems := reg.Rescan()
	for _, p := range problems {
		fmt.Fprintln(os.Stderr, "предупреждение:", p)
	}
	fmt.Fprintf(os.Stderr, "подключено проектов: %d (external-apps: %s)\n", len(loaded), extRoot)
	return reg, nil
}

// ─────────────────────────────────────────────────────────────────────────
// СЕКЦИЯ 4. Подкоманды просмотра и подключения проектов.
// ─────────────────────────────────────────────────────────────────────────

func cmdProjects(args []string) error {
	fs := flag.NewFlagSet("projects", flag.ExitOnError)
	dir := fs.String("dir", "", "рабочий каталог (по умолчанию рядом с exe)")
	format := fs.String("format", "table", "table|json")
	if err := fs.Parse(args); err != nil {
		return err
	}
	reg, err := openStore(*dir)
	if err != nil {
		return err
	}
	projs := reg.Projects()
	if *format == "json" {
		return json.NewEncoder(os.Stdout).Encode(projs)
	}
	if len(projs) == 0 {
		fmt.Println("Проектов нет. Подключите: scg-host add-local <путь> | download <ссылка>")
		return nil
	}
	for _, p := range projs {
		ver := "ветка " + p.Version
		where := "github.com/" + p.Repo
		if p.Source == host.SourceLocal {
			ver = "v" + p.Version
			where = p.Dir // последний указанный путь
		}
		mark := ""
		if !p.Available {
			mark = "  ⚠ папка недоступна"
		}
		fmt.Printf("  %-20s [%s] %-14s %s%s\n", p.Name, p.Source, ver, where, mark)
		if len(p.Executables) == 0 && p.Available {
			fmt.Println("      (нет .exe)")
		}
		for _, e := range p.Executables {
			fmt.Printf("      ▶ %s\n", e)
		}
	}
	return nil
}

func cmdAddLocal(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("ожидалось: add-local <путь к папке проекта> [--dir DIR]")
	}
	path := args[0]
	fs := flag.NewFlagSet("add-local", flag.ExitOnError)
	dir := fs.String("dir", "", "рабочий каталог (по умолчанию рядом с exe)")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	reg, err := openStore(*dir)
	if err != nil {
		return err
	}
	p, err := reg.AddLocalProject(path)
	if err != nil {
		return err
	}
	fmt.Printf("подключён локальный проект %q (%s), версия %s\n", p.Name, p.Dir, p.Version)
	if len(p.Executables) == 0 {
		fmt.Println("  в папке не найдено .exe")
	}
	for _, e := range p.Executables {
		fmt.Println("  ▶", e)
	}
	return nil
}

func cmdDownload(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("ожидалось: download <ссылка на репозиторий> [--dir DIR]")
	}
	repo := args[0]
	fs := flag.NewFlagSet("download", flag.ExitOnError)
	dir := fs.String("dir", "", "рабочий каталог (по умолчанию рядом с exe)")
	if err := fs.Parse(args[1:]); err != nil {
		return err
	}
	reg, err := openStore(*dir)
	if err != nil {
		return err
	}
	p, err := host.DownloadProject(repo, reg.ExternalRoot())
	if err != nil {
		return err
	}
	reg.Rescan() // обновить реестр и сохранённое состояние
	fmt.Printf("проект %q скачан в %s (ветка %s)\n", p.Name, p.Dir, p.Version)
	if len(p.Executables) == 0 {
		fmt.Println("  в проекте не найдено .exe")
	}
	for _, e := range p.Executables {
		fmt.Println("  ▶", e)
	}
	fmt.Printf("запуск: scg-host run-project %s <exe>\n", p.Name)
	return nil
}

// cmdRunProject запускает выбранный .exe проекта КАК ЕСТЬ: аргументы
// пользователем не передаются (симметрично кнопке «Запустить» в Web UI).
func cmdRunProject(args []string) error {
	if len(args) < 2 {
		return fmt.Errorf("ожидалось: run-project <проект> <exe> [--dir DIR]")
	}
	project, exe := args[0], args[1]
	fs := flag.NewFlagSet("run-project", flag.ExitOnError)
	dir := fs.String("dir", "", "рабочий каталог (по умолчанию рядом с exe)")
	timeout := fs.Duration("timeout", 5*time.Minute, "предел ожидания результата")
	if err := fs.Parse(args[2:]); err != nil {
		return err
	}
	reg, err := openStore(*dir)
	if err != nil {
		return err
	}
	jm := host.NewJobManager(reg, &host.Launcher{}, 0)
	job, err := jm.StartProject(project, exe)
	if err != nil {
		return err
	}
	done, err := jm.Wait(job.ID, *timeout)
	if err != nil {
		return err
	}
	if done.Stderr != "" {
		fmt.Fprintln(os.Stderr, "── stderr программы ──")
		fmt.Fprintln(os.Stderr, done.Stderr)
	}
	if done.State != host.JobSucceeded {
		return fmt.Errorf("%s: %s", done.State, done.Error)
	}
	return json.NewEncoder(os.Stdout).Encode(done.Result)
}

// ─────────────────────────────────────────────────────────────────────────
// СЕКЦИЯ 5. Подкоманда serve: HTTP API + Web UI.
// ─────────────────────────────────────────────────────────────────────────

func cmdServe(args []string) error {
	fs := flag.NewFlagSet("serve", flag.ExitOnError)
	dir := fs.String("dir", "", "рабочий каталог (по умолчанию рядом с exe)")
	addr := fs.String("addr", ":8080", "адрес HTTP")
	maxPar := fs.Int("max-parallel", 0, "максимум одновременных процессов (0 — без предела)")
	open := fs.Bool("open", false, "открыть браузер после старта")
	if err := fs.Parse(args); err != nil {
		return err
	}
	return serveOn(*dir, *addr, *maxPar, *open)
}

// serveOn — общий запуск сервера. Порт выбирается умно (ListenSmart): занятый
// :8080 берётся следующим свободным; фактический адрес печатается и, если
// запрошено, открывается в браузере ПОСЛЕ готовности сервера.
func serveOn(dir, addr string, maxParallel int, openWhenReady bool) error {
	reg, err := openStore(dir)
	if err != nil {
		return err
	}
	srv := &host.Server{
		Registry: reg,
		Jobs:     host.NewJobManager(reg, &host.Launcher{}, maxParallel),
	}
	ln, page, err := host.ListenSmart(addr)
	if err != nil {
		return fmt.Errorf("%w\nПодсказка: возможно, порт занят другим приложением или брандмауэр запрещает прослушивание", err)
	}
	if page != "http://localhost"+addr && addr != "" {
		fmt.Fprintf(os.Stderr, "порт из %s занят — выбран свободный\n", addr)
	}
	fmt.Fprintf(os.Stderr, "scg-host: Web UI и API на %s\n", page)
	if openWhenReady {
		go func() {
			for i := 0; i < 50; i++ {
				time.Sleep(100 * time.Millisecond)
				resp, gerr := http.Get(page + "/api/projects")
				if gerr == nil {
					resp.Body.Close()
					openBrowser(page)
					return
				}
			}
			fmt.Fprintln(os.Stderr, "браузер не открыт автоматически — откройте вручную:", page)
		}()
	}
	return http.Serve(ln, srv.Handler())
}
