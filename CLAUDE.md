# CLAUDE.md — контекст проекта scg-host

## Что это за проект
scg-host — управляющее приложение (оркестратор) системы SCG (SCADA
Configuration Governance). Жёсткая граница: хост ИСКЛЮЧИТЕЛЬНО запускает
приложения и показывает их результаты. Никакой предметной логики (разбор
Excel, правила целостности, работа со SCADA) в хосте быть не должно.
Родительский проект SCG (домен `internal/domain` на Go, ТЗ с правилами
целостности A–E, ChangeSet, Findings) ведётся отдельным репозиторием и здесь
отсутствует намеренно.

## Ключевые архитектурные решения (не пересматривать без запроса)
- ПРИЛОЖЕНИЕ = ПРОЕКТ = папка с исполняемыми файлами (.exe). Хост показывает
  список всех .exe проекта; пользователь выбирает нужный и запускает его как
  есть (raw): отдельный процесс ОС, результат {exit_code, stdout}. Никакого
  протокола/манифеста — прежние scg-component/1 и component.json УДАЛЕНЫ.
- ДВА источника проектов (модель симметрична):
  1) ЛОКАЛЬНЫЙ (SourceLocal): путь к папке на машине пользователя
     (AddLocalProject). Используется НА МЕСТЕ — ничего не копируется.
     ПОСЛЕДНИЙ УКАЗАННЫЙ ПУТЬ запоминается в состоянии и восстанавливается
     при старте (LoadState) ДАЖЕ ЕСЛИ папка исчезла: карточка сохраняется
     (Available=false, placeholderLocal — с последней известной версией),
     запуск запрещён (StartProject). Повторный AddLocalProject того же имени
     переподключает на новый путь (побеждает последний указанный).
     Версия — из README проекта (readmeVersion), иначе «—».
  2) GITHUB (SourceGitHub): ОДНА ссылка → DownloadProject качает ВЕСЬ
     репозиторий в подпапку external-apps/ (рядом с exe), пишет
     .scg-project.json (ветка=версия, origin, source_repo→Project.Repo).
     Версия — ветка. Сканируется при каждом старте (scanExternalRoot).
- ДОСТУПНОСТЬ (GET /api/projects/{name}/availability — живая проверка):
  local — существует ли папка по последнему пути; github —
  CheckRepoAvailability: HEAD на codeload той же базой codeloadBase, что и
  скачивание (подменяется в тестах), архив НЕ качается. UI дёргает эндпоинт
  асинхронно (checkAvail) для каждой карточки.
- HostVersion (ids.go, сейчас 0.2.0) — версия хоста, видна в UI и CLI.
- Запуск: JobManager.StartProject(project, exe, args) — проверяет, что exe из
  списка Project.Executables (защита от произвольного пути), затем
  Launcher.Run (raw). findAllExes: сортировка глубина→алфавит.
- Персистентность: scg-apps.json (рядом с exe) — сводка local+external,
  persistState переписывает её при каждом изменении (Rescan, AddLocalProject,
  RemoveProject). Для локальных это ещё и источник восстановления путей.
- Удаление (RemoveProject): github — удаляет подпапку в external-apps;
  локальный — только отвязывает (исходную папку пользователя не трогает).
- ТОЛЬКО stdlib Go (1.22+). Внешние зависимости запрещены (NFR-05/06).
- Порты: ListenSmart — занятый :8080 → 8081..8090 → любой свободный; при уже
  запущенном экземпляре (probeLocal) второй не поднимается, открывается
  существующий. Запуск без аргументов = локальный старт + автооткрытие браузера.
- Рабочий каталог (resolveBaseDir): по умолчанию каталог exe → там
  external-apps/ и scg-apps.json; переопределяется флагом --dir.

## Структура (роли файлов)
- cmd/scg-host/main.go — точка входа; подкоманды projects | add-local |
  download | run-project | serve; launchLocal + probeLocal; openStore
  (external-apps + scg-apps.json, LoadState, Rescan); openBrowser.
- internal/host/ids.go — пакетный док + HostVersion + NewCallID (id заданий).
- internal/host/launcher.go — Launcher.Run: raw-запуск (dir+command+args),
  минимальное окружение, таймаут, WaitDelay=KillGrace (внуки на Windows),
  лимит 16 МиБ, resolveCommand (голое имя сперва ищется в dir), RunResult.
- internal/host/registry.go — Project{Name,Dir,Source,Version,Origin,Repo,
  Available,Executables}; local + external; AddLocalProject (re-point),
  LoadState (пути+seedLocal, без stat), Rescan (placeholderLocal для
  пропавших папок), RemoveProject, persistState; readmeVersion.
- internal/host/github.go — ParseGitHubRepo, DownloadProject, findAllExes,
  downloadRepoZip (main→master), extractRepoZip (zip-slip защита, exec-биты),
  loadProject (Source=github, Repo из меты), projectMeta/.scg-project.json,
  CheckRepoAvailability + repoFromOrigin, ExternalAppsDirName="external-apps".
- internal/host/jobs.go — Job{Project,Executable,Args}; JobManager.StartProject
  (через Launcher.Run; недоступный проект отвергается), Cancel, Wait,
  List/Get, семафор --max-parallel.
- internal/host/server.go — только HTTP API: /api/projects (+rescan),
  /api/projects/local, /api/projects/github, /api/projects/{name}/run,
  /remove, /availability; /api/jobs*.
- internal/host/ui.go — uiHTML (Web UI, html/template, без CDN): две формы,
  карточки (версия; local — последний путь; github — репозиторий;
  доступность через checkAvail), таблица заданий. БЕЗ backtick внутри!
- internal/host/listen.go — ListenSmart/PortOf.

## Правила работы для агента
- Русский язык в UI, ошибках, комментариях и документации. Ошибки — адресные,
  с подсказкой действия.
- Тесты обязательны для новой логики; интеграционные — с requireSh(t)
  (skip без sh). Реальный запуск .exe в тестах непереносим, поэтому
  Launcher.Run тестируется через sh, а проекты — с фейковыми .exe (проверяем
  список/валидацию/персистентность, не факт исполнения). go test ./... зелёный.
- Детерминированность: сортировать выводы (проекты, .exe), не использовать
  время/случайность в идентичности.
- После правок server.go проверять: каждый маршрут в Handler() имеет метод,
  все *Body-типы определены.
- Известные классы дефектов: (1) \n в строковых литералах не должен стать
  реальным переносом; (2) в Go raw-строке uiHTML (в backtick) НЕЛЬЗЯ ставить
  backtick внутри — закроет литерал (был инцидент с `.exe` в тексте).
- README.md — часть поставки: любое изменение поведения отражать в нём.
  Писать в том числе для неспециалистов.
- ПОСТАВКА: после ЛЮБОГО изменения проекта собирать bin/scg-host.exe
  (go build -o bin/scg-host.exe ./cmd/scg-host) и коммитить его вместе с
  изменениями в github (origin: KovalenkoNS/Host) — репозиторий всегда
  содержит актуальный готовый .exe (директива пользователя, 2026-07-23).
- Не выполнять запись в SCADA и не тащить сюда предметную логику SCG.

## Сборка и проверка
    go build -o bin/scg-host ./cmd/scg-host      # Windows: bin\scg-host.exe
    go test ./...
    bin/scg-host                                 # локальный старт + браузер
    bin/scg-host serve --open

## Текущее состояние / открытые направления
- Хост функционально завершён (v0.2.0), собирается и работает на Windows.
- Репозиторий связан с https://github.com/KovalenkoNS/Host (origin, ветка main).
- .exe — программы Windows: на Linux/macOS github-проекты с .exe не запустятся
  (локальные проекты могут содержать exe под текущую ОС).
- Следующий крупный шаг родительского SCG: Этап 2 (append-only журнал,
  snapshot, replay) как первый «настоящий» проект хоста.
- Возможные улучшения: проверка обновлений github-репозитория, поддержка
  не-.exe исполняемых для локальных проектов, ограничение изоляции
  ОС-средствами (ADR).
