SHELL := /bin/bash

# Single source of truth for what can be built.
COMPONENTS := compA compB compC
LOGDIR     := logs

# Which components this invocation builds: the component names given on the
# command line (e.g. `make compA` or `make compA compC`), or ALL of them when
# none are named (`make` / `make all`).
SELECTED := $(filter $(COMPONENTS),$(MAKECMDGOALS))
ifeq ($(SELECTED),)
  SELECTED := $(COMPONENTS)
endif

BUILD_TARGETS := $(addprefix build-,$(COMPONENTS))

.PHONY: all clean log $(COMPONENTS) $(BUILD_TARGETS)

# Default goal. `make` and `make all` build every component.
all: log

# User-facing per-component target, so `make compA` works. It builds just that
# component and then (re)assembles the combined log for what was selected.
# The @: no-op recipe suppresses make's "Nothing to be done" notice when more
# than one component is named on the command line.
$(COMPONENTS): %: build-% log
	@:

# Real build rule for one component. Under `make -j` the selected components'
# build-* targets run in parallel. pipefail keeps the sub-make's exit code from
# being masked by the `| tee`.
$(BUILD_TARGETS): build-%: | $(LOGDIR)
	@set -o pipefail; $(MAKE) --no-print-directory -C $* 2>&1 | tee $(LOGDIR)/$*.log

# Assemble the combined log AFTER the selected builds finish, in fixed order.
# Depending on the selected build-* targets is what orders this after them and
# keeps logs/build.log byte-identical regardless of parallel finish order.
log: $(addprefix build-,$(SELECTED))
	@for c in $(SELECTED); do echo "=== $$c ==="; cat $(LOGDIR)/$$c.log; done > $(LOGDIR)/build.log

$(LOGDIR):
	@mkdir -p $(LOGDIR)

clean:
	@for c in $(COMPONENTS); do $(MAKE) --no-print-directory -C $$c clean; done
	@rm -rf $(LOGDIR)
