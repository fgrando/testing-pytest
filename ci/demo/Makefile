CC  ?= gcc
OUT := out

all: $(OUT)/tiboot3.raw

# Compile, then treat the result as the raw boot image to be signed.
# (A real K3 build would objcopy the SPL ELF to a flat binary here.)
$(OUT)/tiboot3.raw: main.c | $(OUT)
	$(CC) -O2 -o $(OUT)/main.elf main.c
	cp $(OUT)/main.elf $(OUT)/tiboot3.raw

$(OUT):
	mkdir -p $(OUT)

clean:
	rm -rf $(OUT)

.PHONY: all clean
