import logging
import re

import nidaqmx_python_generator.helpers as helpers

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


# We don't need this stuff.
ENUMS_BLACKLIST = [
    "AIMeasurementType",
    "AOOutputChannelType",
    "CIMeasurementType",
    "COOutputType",
    "AltRef",
    "AntStatus",
    "CalibrationTerminalConfig",
    "NavMeasurementType",
    "NavMode",
    "SaveOptions"
]


# Metadata issues or invalid Python names (leading number)
NAME_SUBSTITUTIONS = {
    '100_MHZ_TIMEBASE': 'ONE_HUNDRED_MHZ_TIMEBASE',
    '10134': 'CURRENT',
    '10322': 'VOLTAGE',
    '12527': 'HIGH_IMPEDANCE',
    '20_MHZ_TIMEBASE': 'TWENTY_MHZ_TIMEBASE',
    '2POINT_5_V': 'TWO_POINT_FIVE_V',
    '2_WIRE': 'TWO_WIRE',
    '3POINT_3_V': 'THREE_POINT_THREE_V',
    '3_WIRE': 'THREE_WIRE',
    '4_WIRE': 'FOUR_WIRE',
    '5_V': 'FIVE_V',
    '5_WIRE': 'FIVE_WIRE',
    '6_WIRE': 'SIX_WIRE',
    '80_MHZ_TIMEBASE': 'EIGHTY_MHZ_TIMEBASE',
    '8_MHZ_TIMEBASE': 'EIGHT_MHZ_TIMEBASE',
    'ACCEL_UNIT_G': 'G',
    'LOGIC_LEVEL_PULL_UP': 'PULL_UP',
    'MILLI_VOLTS': 'MILLIVOLTS',
    'M_VOLTS': 'MILLIVOLTS',
    'ON_BRD': 'ONBRD',
    'PC_IE': 'PCIE',
    'PX_IE': 'PXIE',
}

ENUM_MERGE_SET = {
    "CurrentShuntResistorLocation": ["CurrentShuntResistorLocation1", "CurrentShuntResistorLocationWithDefault"],
    "InputTermCfg": ["InputTermCfg2", "InputTermCfgWithDefault"],
}

# TODO: Where are these? (if unused, that's fine)
# Action (Commit, Cancel)
# ActiveOrInactiveEdgeSelection
# BreakMode
# BridgeConfiguration (QUARTER_BRIDGE_120_OHM_COMPLETION_RESISTOR, QUARTER_BRIDGE_350_OHM_COMPLETION_RESISTOR)
# CalibrationTerminalConfig
# EndCalAction
# FillMode (now GroupBy???)
# ExportAction (ExportActions was added... odd)
# FilterResponse (CONSTANT_GROUP_DELAY, ELLIPTICAL, HARDWARE_DEFINED)
# Level (NO_CHANGE, TRISTATE)
# PathCapability
# RelayPosition
# ScaleType (Linear, Map Ranges)
# ScanRepeatMode
# ShuntElementLocation
# ShuntResistorSelect
# Signal (lots of values)
# SignalModifiers
# TaskMode (now TaskControlAction)
# TaskState
# UsageTypeAI, AO, CI, CO
# WDTTaskAction
# WatchdogTaskAction (WatchdogControlAction)
# bitfield types

# 22.5 stuff:
# TestScale/Power

def _merge_enum_values(valueses):
    result_set = {}
    for values_array in valueses:
        for value in values_array:
            value_num = value['value']
            result_set[value_num] = value
    return list(result_set.values())


def _merge_enum_variants(enums):
    # Combine the numbered enum variants. These exist to give remove options that aren't applicable
    # for some attributes in interactive environments like G Controls/Indicators and CVI Function
    # Panels.
    name_pattern = re.compile("(.*\D)(\d+)")

    enum_merge_set = ENUM_MERGE_SET

    in_a_run = False
    enums_in_run = []

    for list_index, enum_name in enumerate(sorted(enums.keys())):
        match = name_pattern.fullmatch(enum_name)
        if match:
            basename = match.group(1)
            instance = int(match.group(2))

            if in_a_run:
                if basename == run_basename:
                    enums_in_run.append(enum_name)
                else:
                    # queue up the last batch ...
                    enum_merge_set[run_basename] = enums_in_run
                    # ... and start a new one
                    if basename not in enum_merge_set:
                        run_basename = basename
                        enums_in_run = [enum_name]
            elif basename not in enum_merge_set:
                # start a new run
                in_a_run = True
                run_basename = basename
                enums_in_run = [enum_name]
        elif in_a_run:
            # queue up the last batch ...
            enum_merge_set[run_basename] = enums_in_run
            # ... and we're done
            in_a_run = False

    for basename, enums_to_merge in enum_merge_set.items():
        _logger.debug(f"merging enums: {basename} <-- {enums_to_merge}")
        enums[basename] = {
            'values': _merge_enum_values([enums[enum]['values'] for enum in enums_to_merge])
        }
        # delete the variants, now
        for enum in enums_to_merge:
            if not enum == basename:
                del enums[enum]

    # sort it by key (enum name)
    return dict(sorted(enums.items()))


def _sanitize_values(enums):
    for enum_name, enum in enums.items():
        for value in enum['values']:
            value_name = value['name']
            for old, new in NAME_SUBSTITUTIONS.items():
                value_name = value_name.replace(old, new)
            value['name'] = value_name
    return enums


def get_enums(metadata):
    enums = metadata['enums']

    # First remove enums we don't use.
    enums = {name: val for (name, val) in enums.items() if name not in ENUMS_BLACKLIST}
    # Then merge variants.
    enums = _merge_enum_variants(enums)
    return _sanitize_values(enums)


def get_enum_value_docstring(enum_value):
    if 'documentation' in enum_value and 'description' in enum_value['documentation']:
        raw_docstring = helpers.cleanup_docstring(enum_value['documentation']['description'])
        return f"  #: {raw_docstring}"
    return ""