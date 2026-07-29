/*
 * TCP AESP client bench: exercise the portable C client against V-ECU.
 *
 * Usage: ecu_tcp_bench <host> <port>
 * Expects V-ECU greeting line, then runs sign → write → burn → powercycle → read.
 * Exit 0 on success.
 */
#include "gcu/ecu_client.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET sock_t;
#define CLOSESOCK closesocket
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int sock_t;
#define INVALID_SOCKET (-1)
#define CLOSESOCK close
#endif

typedef struct {
  sock_t fd;
  char rbuf[4096];
  size_t rlen;
} tcp_ctx_t;

static int tcp_write_line(void *ctx, const char *line) {
  tcp_ctx_t *t = (tcp_ctx_t *)ctx;
  char buf[1024];
  int n = snprintf(buf, sizeof buf, "%s\n", line);
  if (n <= 0 || (size_t)n >= sizeof buf) {
    return -1;
  }
#if defined(_WIN32)
  return send(t->fd, buf, n, 0) == n ? 0 : -1;
#else
  return (int)write(t->fd, buf, (size_t)n) == n ? 0 : -1;
#endif
}

static int tcp_read_line(void *ctx, char *out, size_t out_len) {
  tcp_ctx_t *t = (tcp_ctx_t *)ctx;
  for (;;) {
    size_t i;
    for (i = 0; i < t->rlen; i++) {
      if (t->rbuf[i] == '\n') {
        size_t linelen = i;
        if (linelen > 0 && t->rbuf[linelen - 1] == '\r') {
          linelen -= 1;
        }
        if (linelen + 1 > out_len) {
          return -1;
        }
        memcpy(out, t->rbuf, linelen);
        out[linelen] = '\0';
        memmove(t->rbuf, t->rbuf + i + 1, t->rlen - i - 1);
        t->rlen -= i + 1;
        return 0;
      }
    }
    if (t->rlen >= sizeof t->rbuf - 1) {
      return -1;
    }
    {
#if defined(_WIN32)
      int n = recv(t->fd, t->rbuf + t->rlen, (int)(sizeof t->rbuf - 1 - t->rlen), 0);
#else
      ssize_t n = read(t->fd, t->rbuf + t->rlen, sizeof t->rbuf - 1 - t->rlen);
#endif
      if (n <= 0) {
        return -1;
      }
      t->rlen += (size_t)n;
    }
  }
}

static sock_t connect_tcp(const char *host, int port) {
  sock_t fd;
  struct sockaddr_in addr;
#if defined(_WIN32)
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
    return INVALID_SOCKET;
  }
#endif
  fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd == INVALID_SOCKET) {
    return INVALID_SOCKET;
  }
  memset(&addr, 0, sizeof addr);
  addr.sin_family = AF_INET;
  addr.sin_port = htons((unsigned short)port);
  if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
    CLOSESOCK(fd);
    return INVALID_SOCKET;
  }
  if (connect(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
    CLOSESOCK(fd);
    return INVALID_SOCKET;
  }
  return fd;
}

int main(int argc, char **argv) {
  const char *host;
  int port;
  tcp_ctx_t tcp;
  gcu_ecu_client_t c;
  gcu_ecu_transport_t t;
  char greet[128];
  char sig[96];
  char crc_before[16];
  char crc_after[16];
  uint8_t patch[2] = {0x12, 0x34};
  uint8_t got[2];

  if (argc != 3) {
    fprintf(stderr, "usage: %s <host> <port>\n", argv[0]);
    return 2;
  }
  host = argv[1];
  port = atoi(argv[2]);

  memset(&tcp, 0, sizeof tcp);
  tcp.fd = connect_tcp(host, port);
  if (tcp.fd == INVALID_SOCKET) {
    fprintf(stderr, "connect failed\n");
    return 1;
  }

  t.write_line = tcp_write_line;
  t.read_line = tcp_read_line;
  t.ctx = &tcp;
  gcu_ecu_client_init(&c, t);

  if (tcp_read_line(&tcp, greet, sizeof greet) != 0) {
    fprintf(stderr, "no greeting\n");
    return 1;
  }
  if (strncmp(greet, "AESP", 4) != 0) {
    fprintf(stderr, "bad greeting: %s\n", greet);
    return 1;
  }

  if (gcu_ecu_sign(&c, sig, sizeof sig) != 0) {
    fprintf(stderr, "sign failed\n");
    return 1;
  }
  if (gcu_ecu_flash_crc_all(&c, crc_before) != 0) {
    fprintf(stderr, "flashcrc before failed\n");
    return 1;
  }
  if (gcu_ecu_write_ram(&c, 0, 0, patch, 2) != 0) {
    fprintf(stderr, "write failed\n");
    return 1;
  }
  if (gcu_ecu_burn_all(&c) != 0) {
    fprintf(stderr, "burn failed\n");
    return 1;
  }
  if (gcu_ecu_power_cycle(&c) != 0) {
    fprintf(stderr, "powercycle failed\n");
    return 1;
  }
  if (gcu_ecu_read_ram(&c, 0, 0, 2, got, sizeof got) != 0) {
    fprintf(stderr, "read failed\n");
    return 1;
  }
  if (got[0] != patch[0] || got[1] != patch[1]) {
    fprintf(stderr, "persist mismatch\n");
    return 1;
  }
  if (gcu_ecu_flash_crc_all(&c, crc_after) != 0) {
    fprintf(stderr, "flashcrc after failed\n");
    return 1;
  }
  if (strcmp(crc_before, crc_after) == 0) {
    fprintf(stderr, "crc did not change after burn\n");
    return 1;
  }

  printf("ecu_tcp_bench: OK sign=%s flash_crc=%s\n", sig, crc_after);
  CLOSESOCK(tcp.fd);
#if defined(_WIN32)
  WSACleanup();
#endif
  return 0;
}
