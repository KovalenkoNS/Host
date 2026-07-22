package host

import (
	"fmt"
	"net"
	"strconv"
)

// ListenSmart пытается занять предпочтительный адрес (например ":8080").
// Если порт занят — перебирает следующие 10 портов, затем берёт любой
// свободный (":0"). Возвращает слушатель и URL страницы для человека.
//
// Это устраняет типовой отказ Windows:
// "bind: Only one usage of each socket address ... is normally permitted"
// при повторном запуске или занятом порту.
func ListenSmart(preferred string) (net.Listener, string, error) {
	ln, firstErr := net.Listen("tcp", preferred)
	if firstErr == nil {
		return ln, pageURL(ln), nil
	}
	hostPart, portStr, err := net.SplitHostPort(preferred)
	if err != nil {
		return nil, "", firstErr
	}
	port, err := strconv.Atoi(portStr)
	if err != nil {
		return nil, "", firstErr
	}
	for p := port + 1; p <= port+10; p++ {
		if ln, e := net.Listen("tcp", net.JoinHostPort(hostPart, strconv.Itoa(p))); e == nil {
			return ln, pageURL(ln), nil
		}
	}
	if ln, e := net.Listen("tcp", net.JoinHostPort(hostPart, "0")); e == nil {
		return ln, pageURL(ln), nil
	}
	return nil, "", fmt.Errorf("не удалось занять ни один порт, начиная с %s: %w", preferred, firstErr)
}

// pageURL — адрес страницы для открытия в браузере на этой же машине.
func pageURL(ln net.Listener) string {
	if tcp, ok := ln.Addr().(*net.TCPAddr); ok {
		return fmt.Sprintf("http://localhost:%d", tcp.Port)
	}
	return "http://localhost" // недостижимо для tcp-слушателя
}

// PortOf — номер порта слушателя (для сообщений).
func PortOf(ln net.Listener) int {
	if tcp, ok := ln.Addr().(*net.TCPAddr); ok {
		return tcp.Port
	}
	return 0
}
