CC       := gcc
CFLAGS   := -shared -fPIC -fvisibility=default \
            $(shell pkg-config --cflags wayland-client)
LDFLAGS  := -lwayland-client
SOURCES  := blur.c ext-background-effect-v1-protocol.c
TARGET   := libblur.so

all: $(TARGET)

$(TARGET): $(SOURCES) blur.h ext-background-effect-v1-client-protocol.h
	$(CC) $(CFLAGS) -o $@ $(SOURCES) $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean
