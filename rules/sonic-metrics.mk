# sonic-metrics python2 wheel package

SONIC_METRICS = sonic_metrics-1.0-py2-none-any.whl
$(SONIC_METRICS)_SRC_PATH = $(SRC_PATH)/sonic-metrics
$(SONIC_METRICS)_DEPENDS += $(SWSSSDK_PY2) $(SONIC_PY_COMMON_PY2)
$(SONIC_METRICS)_PYTHON_VERSION = 2
SONIC_PYTHON_WHEELS += $(SONIC_METRICS)

export sonic_metrics_py2_wheel_path="$(addprefix $(PYTHON_WHEELS_PATH)/,$(SONIC_METRICS))"
