package host

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// DefaultTimeout — таймаут запуска, если не задан свой.
const DefaultTimeout = 300 * time.Second

// MaxOutputBytes — предохранитель от программы, заливающей хост выводом.
const MaxOutputBytes = 16 << 20 // 16 МиБ

// KillGrace — сколько ждать закрытия stdout/stderr после того, как истёк
// таймаут или запуск отменён, прежде чем принудительно закрыть каналы.
// Нужно на Windows: exec.CommandContext убивает только прямой процесс; если
// тот породил дочерний, внук наследует каналы вывода и держит их открытыми —
// без WaitDelay cmd.Wait() завис бы до завершения внука.
const KillGrace = 1 * time.Second

// Launcher запускает исполняемый файл проекта (режим raw) в изоляции:
//   - каждый запуск = новый процесс ОС;
//   - рабочий каталог — папка проекта;
//   - окружение минимально (PATH, HOME, LANG, LC_ALL, TMPDIR, SystemRoot);
//   - принудительное завершение по таймауту, лимит вывода.
type Launcher struct {
	Timeout time.Duration // 0 → DefaultTimeout
}

// RunResult — итог запуска: код выхода и захваченный вывод.
type RunResult struct {
	ExitCode int
	Stdout   string
	Stderr   string
	Duration time.Duration
}

// Run запускает command с аргументами args в рабочем каталоге dir.
// Относительная команда без разделителей пути (например app.exe) сперва
// ищется В dir; иначе — обычный поиск в PATH. Ненулевой код выхода — не
// ошибка запуска: он возвращается в RunResult.ExitCode. Ошибка (err != nil)
// означает, что программу не удалось запустить, таймаут или отмену.
func (l *Launcher) Run(ctx context.Context, dir, command string, args []string, timeoutSec int) (*RunResult, error) {
	timeout := l.Timeout
	if timeout <= 0 {
		timeout = DefaultTimeout
	}
	if timeoutSec > 0 {
		timeout = time.Duration(timeoutSec) * time.Second
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, resolveCommand(dir, command), args...)
	cmd.Dir = dir
	cmd.Env = minimalEnv()
	cmd.WaitDelay = KillGrace

	var stdout, stderr limitedBuffer
	stdout.limit, stderr.limit = MaxOutputBytes, MaxOutputBytes
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	start := time.Now()
	runErr := cmd.Run()
	dur := time.Since(start)
	res := &RunResult{Stdout: stdout.String(), Stderr: stderr.String(), Duration: dur}

	if ctx.Err() == context.DeadlineExceeded {
		return res, fmt.Errorf("превышен таймаут %s", timeout)
	}
	if ctx.Err() == context.Canceled {
		return res, fmt.Errorf("выполнение отменено")
	}
	if runErr != nil {
		var ee *exec.ExitError
		if errors.As(runErr, &ee) {
			res.ExitCode = ee.ExitCode()
			return res, nil // ненулевой код — отражаем в результате, не ошибка
		}
		return res, fmt.Errorf("не удалось запустить %q: %w", command, runErr)
	}
	return res, nil
}

// resolveCommand: абсолютная команда или из PATH — как есть; путь с
// разделителями — относительно dir; голое имя (app.exe) — сперва в dir,
// иначе поиск в PATH.
func resolveCommand(dir, c string) string {
	if filepath.IsAbs(c) {
		return c
	}
	if strings.ContainsRune(c, '/') || strings.ContainsRune(c, os.PathSeparator) ||
		strings.HasPrefix(c, "./") || strings.HasPrefix(c, "../") {
		return filepath.Join(dir, c)
	}
	if p := filepath.Join(dir, c); fileExists(p) {
		return p
	}
	return c
}

func fileExists(p string) bool {
	st, err := os.Stat(p)
	return err == nil && !st.IsDir()
}

// minimalEnv — минимальное окружение процесса приложения.
func minimalEnv() []string {
	keep := []string{"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SystemRoot"}
	env := make([]string, 0, len(keep))
	for _, k := range keep {
		if v, ok := os.LookupEnv(k); ok {
			env = append(env, k+"="+v)
		}
	}
	return env
}

// limitedBuffer — буфер с верхней границей размера.
type limitedBuffer struct {
	buf   []byte
	limit int
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	if len(b.buf)+len(p) > b.limit {
		return 0, fmt.Errorf("превышен предел вывода %d байт", b.limit)
	}
	b.buf = append(b.buf, p...)
	return len(p), nil
}

func (b *limitedBuffer) String() string { return string(b.buf) }
