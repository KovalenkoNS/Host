package host

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"sync"
	"time"
)

// JobState — состояние запуска.
type JobState string

const (
	JobRunning   JobState = "running"
	JobSucceeded JobState = "succeeded"
	JobFailed    JobState = "failed"
	JobCancelled JobState = "cancelled"
)

// Job — один запуск исполняемого файла проекта, выполняемый параллельно
// с другими. Каждый Job — отдельная горутина хоста и отдельный процесс ОС.
// Аргументы пользователем НЕ передаются: файл запускается как есть, кнопкой.
type Job struct {
	ID         string          `json:"id"`
	Project    string          `json:"project"`
	Executable string          `json:"executable"`
	State      JobState        `json:"state"`
	StartedAt  time.Time       `json:"started_at"`
	EndedAt    *time.Time      `json:"ended_at,omitempty"`
	Result     json.RawMessage `json:"result,omitempty"`
	Error      string          `json:"error,omitempty"`
	Stderr     string          `json:"stderr,omitempty"`
	DurationMS int64           `json:"duration_ms"`

	cancel context.CancelFunc
}

// JobManager — параллельный запуск и наблюдение. Ограничение параллелизма —
// семафор maxParallel (0 = без ограничения).
type JobManager struct {
	registry *Registry
	launcher *Launcher

	mu   sync.RWMutex
	jobs map[string]*Job
	sem  chan struct{}
}

// NewJobManager — менеджер над реестром и лаунчером.
func NewJobManager(reg *Registry, l *Launcher, maxParallel int) *JobManager {
	var sem chan struct{}
	if maxParallel > 0 {
		sem = make(chan struct{}, maxParallel)
	}
	return &JobManager{registry: reg, launcher: l, jobs: map[string]*Job{}, sem: sem}
}

// StartProject запускает выбранный исполняемый файл проекта асинхронно и сразу
// возвращает Job в состоянии running. exe должен быть из списка
// Project.Executables (путь вне списка отвергается — защита от запуска
// произвольного файла). Файл запускается КАК ЕСТЬ, без аргументов —
// пользователь только нажимает кнопку. Ошибки конфигурации — синхронно.
func (jm *JobManager) StartProject(project, exe string) (*Job, error) {
	p, ok := jm.registry.GetProject(project)
	if !ok {
		return nil, fmt.Errorf("проект %q не подключён", project)
	}
	if !p.Available {
		return nil, fmt.Errorf("папка проекта %q недоступна (последний путь: %s) — верните папку на место или подключите заново", project, p.Dir)
	}
	allowed := false
	for _, e := range p.Executables {
		if e == exe {
			allowed = true
			break
		}
	}
	if !allowed {
		return nil, fmt.Errorf("в проекте %q нет исполняемого файла %q", project, exe)
	}

	ctx, cancel := context.WithCancel(context.Background())
	job := &Job{
		ID:         NewCallID(),
		Project:    project,
		Executable: exe,
		State:      JobRunning,
		StartedAt:  time.Now().UTC(),
		cancel:     cancel,
	}
	jm.mu.Lock()
	jm.jobs[job.ID] = job
	jm.mu.Unlock()

	go jm.run(ctx, job, p.Dir)
	return job, nil
}

func (jm *JobManager) run(ctx context.Context, job *Job, dir string) {
	if jm.sem != nil {
		jm.sem <- struct{}{}
		defer func() { <-jm.sem }()
	}
	res, err := jm.launcher.Run(ctx, dir, job.Executable, nil, 0)

	jm.mu.Lock()
	defer jm.mu.Unlock()
	now := time.Now().UTC()
	job.EndedAt = &now
	if res != nil {
		job.Stderr = res.Stderr
		job.DurationMS = res.Duration.Milliseconds()
	}
	switch {
	case ctx.Err() == context.Canceled:
		job.State = JobCancelled
		job.Error = "запуск отменён человеком"
	case err != nil:
		job.State = JobFailed
		job.Error = err.Error()
	case res.ExitCode != 0:
		job.State = JobFailed
		job.Error = fmt.Sprintf("программа завершилась с кодом %d", res.ExitCode)
		job.Result, _ = json.Marshal(map[string]any{"exit_code": res.ExitCode, "stdout": res.Stdout})
	default:
		job.State = JobSucceeded
		job.Result, _ = json.Marshal(map[string]any{"exit_code": 0, "stdout": res.Stdout})
	}
}

// Cancel — отмена выполняющегося запуска (процессу посылается SIGKILL
// через контекст).
func (jm *JobManager) Cancel(id string) bool {
	jm.mu.RLock()
	job, ok := jm.jobs[id]
	jm.mu.RUnlock()
	if !ok || job.State != JobRunning {
		return false
	}
	job.cancel()
	return true
}

// Get — задание по ID (копия, безопасная для сериализации).
func (jm *JobManager) Get(id string) (Job, bool) {
	jm.mu.RLock()
	defer jm.mu.RUnlock()
	j, ok := jm.jobs[id]
	if !ok {
		return Job{}, false
	}
	return *j, true
}

// List — все задания, новые первыми (детерминированно по времени, затем ID).
func (jm *JobManager) List() []Job {
	jm.mu.RLock()
	defer jm.mu.RUnlock()
	out := make([]Job, 0, len(jm.jobs))
	for _, j := range jm.jobs {
		out = append(out, *j)
	}
	sort.Slice(out, func(i, k int) bool {
		if !out[i].StartedAt.Equal(out[k].StartedAt) {
			return out[i].StartedAt.After(out[k].StartedAt)
		}
		return out[i].ID < out[k].ID
	})
	return out
}

// Wait блокируется до завершения задания или истечения timeout (для CLI).
func (jm *JobManager) Wait(id string, timeout time.Duration) (Job, error) {
	deadline := time.Now().Add(timeout)
	for {
		j, ok := jm.Get(id)
		if !ok {
			return Job{}, fmt.Errorf("задание %s не найдено", id)
		}
		if j.State != JobRunning {
			return j, nil
		}
		if time.Now().After(deadline) {
			return j, fmt.Errorf("ожидание задания %s превысило %s", id, timeout)
		}
		time.Sleep(20 * time.Millisecond)
	}
}
