#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LogAnalyzer: python script analyzes nginx's log files.

Usage:  log_analyzer.py [options]

Options:
    -c FILE_INI --config=FILE_INI   Config file [default: log_analyzer.ini]
    -i                              Write default ini config settings to FILE_INI
    -h  --help                      Show this screen.
    --version                       Show version.
    -v                              Run doc tests.
"""

__version__ = 'v0.1.0'

import logging
import logging.config
import os
import sys
import re
import copy
import gzip
import bz2
from datetime import datetime
from pathlib import Path
import collections as cs
from docopt import docopt, DocoptExit                     # https://pypi.org/project/docopt/
from configparser import ConfigParser, RawConfigParser    # https://docs.python.org/3/library/configparser.html
from string import Template
import json
from contextlib import suppress
from operator import itemgetter
from statistics import median
import unittest
import pycodestyle


class classproperty(property):
    """Make class properties available by using @classproperty decorator."""

    def __get__(self, cls, owner):
        """Make classmethod call being used as classproperty calling __get__."""
        return classmethod(self.fget).__get__(None, owner)()


class App:
    """
    class App - service class provides resolved config settings and tuned logger for main app.

    >>> sorted(list((k, list(sorted(v.keys()))) for k, v in App._App__config.items()))
    [('App', ['VERSION']),
    ('Logging', ['BASE_CONFIG_DATEFMT', 'BASE_CONFIG_FILEMODE', 'BASE_CONFIG_FILENAME', 'BASE_CONFIG_FORMAT', 'BASE_CONFIG_LEVEL', 'FILE_CFG', 'LOGGER_NAME']),
    ('Logs', ['DIR', 'FILE_NAME_DATE_FORMAT', 'FILE_NAME_PREFIX', 'LINE_FORMAT']),
    ('Report', ['DIR', 'FILE_NAME_DATE_FORMAT', 'FILE_NAME_PREFIX', 'FILE_NAME_EXT', 'REPORT_SIZE'])]
    >>> logs_dir = App.resolve_path(App.cfg.Logs.DIR)
    >>> 1 if logs_dir.exists() and os.access(logs_dir, os.F_OK) else 0
    1
    """
    REQUIRED_PYTHON_VER = (3, 9)
    ENCONDING = "utf-8"
    ROUND_NDIGITS = 4

    __default_config = {
        'App': {
            'VERSION': __version__  # version of external config ini should be like '*.*' of __version__
        },
        'Report': {
            'DIR': 'reports',  # directory in which logs are located.
            'FILE_NAME_PREFIX': 'nginx-access-ui.report-',  # report file path is Report.DIR / FILE_NAME_PREFIX + date in FILE_NAME_DATE_FORMAT + FILE_NAME_EXT
            'FILE_NAME_DATE_FORMAT': '%Y%m%d',
            'FILE_NAME_EXT': None,  # if None, then report extension is the same as for template.
            'REPORT_SIZE': '1000',  # Мaximum number of urls in report output sorted by total time (desc). if None, then all.
            'TEMPLATE_FILE_PATH': 'reports/report.html'  # Path to template file
        },
        'Logs': {
            'DIR':   'logs',  # log files dir
            'FILE_NAME_PREFIX': 'nginx-access-ui.log-',  # log file path is Logs.DIR / FILE_NAME_PREFIX + date in FILE_NAME_DATE_FORMAT + any extention (todo: non any)
            'FILE_NAME_DATE_FORMAT': '%Y%m%d',
            'LINE_FORMAT': r'^(?P<remote_addr>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\s+\S+\s+\S+\s+\[(?P<time_local>.+)\]\s+"'
                           r'(?P<request_method>[A-Z]+)\s+(?P<request_url>[\w\.\-\/]+)(?P<request_params>\?[\S]*)*\s+(?P<protocol>.*?)"\s+(?P<status>\d{3})\s+'
                           r'(?P<body_bytes_sent>\d+)\s+\S+\s+"(?P<http_user_agent>.*?)".*?(?P<request_time>[\d\.]*)$',  # reg expression that should identify <request_url> and <request_time> fields in log. the rest is not used (yet)...
            'UNMATCHED_LINE_LIMIT': '0.1'  # allowed number of errors for log parsing (in percent). if there are more, then exit with error.
        },
        'Logging': {
            'LOGGER_NAME': '__name__',  # app logger = logging.getLogger('LOGGER_NAME')
            'BASE_CONFIG_FORMAT': '[%(asctime)s] %(levelname).1s %(message)s',
            'BASE_CONFIG_DATEFMT': '%Y.%m.%d %H:%M:%S',
            'BASE_CONFIG_LEVEL': 'DEBUG',
            'BASE_CONFIG_FILENAME': None,   # 'log_analyzer.log',
            'BASE_CONFIG_FILEMODE': None,   # 'w'|'a'
            'FILE_CFG': 'logging.ini',      # higher priority over BASE_CONFIG settings
        }
    }
    __config = __default_config
    __logger_name = __name__
    __logger = None

    @classproperty
    def logger(cls):
        """Return logging.logger: app configurated logger."""
        if cls.__logger is None:
            cls.__logger = logging.getLogger(cls.__logger_name)
        return cls.__logger

    @classproperty
    def cfg(cls):
        """Return named tuple instance [AppConfig] of config settings [dict]."""
        return cls.nt(cls.__config, 'AppConfig')

    @staticmethod
    def resolve_path(path: str) -> Path:
        """
        Resolve path [str] using expanuser and resolve method of Path. Return resolved Path instance.

        1. expanduser: return a new path with expanded ~ and ~user constructs
        2. resolve: make the path absolute, resolving all symlinks on the way and also
           normalizing it (for example turning slashes into backslashes under Windows).
        """
        return Path(path).expanduser().resolve()

    @staticmethod
    def nt(obj, name: str = None):
        """
        Return a copy of [obj] with converted (any level) items of dict types -> named tuple, list/tuple -> tuple, obj -> copy(obj) #todo: propose smt better than copy of obj...

        Doctest examples:
        >>> d = {'a': {'a1': 1, 'a2': 2}, 'b': {'b1': 10, 'b2': 20}}
        >>> dnt = App.nt(d, 'dnt')
        >>> dnt
        dnt(a=a(a1=1, a2=2), b=b(b1=10, b2=20))
        >>> dnt.b.b2
        20
        """
        if isinstance(obj, dict):
            _obj = obj.copy()
            for key, value in _obj.items():
                _obj[key] = App.nt(value, key)  # ! key should be valid name
            return cs.namedtuple(name if name else f'nt{id(_obj)}', _obj.keys())(**_obj)
        elif isinstance(obj, (list, tuple)):
            return tuple(App.nt(item) for item in obj)
        else:
            return copy.copy(obj)

    @classmethod
    def save_config(cls, to_file_path: str, config: dict = None) -> None:
        """Save [config: dict] to file [to_file_path], if [config] is None then [config] = App default config."""
        config = config or cls.__default_config
        config_parser = ConfigParser(allow_no_value=True, interpolation=None)
        config_parser.optionxform = str
        for key in config:
            config_parser[key] = config[key]
        with open(to_file_path, 'w', encoding=cls.ENCONDING) as config_file:
            config_parser.write(config_file)

    @staticmethod
    def load_config(path: str) -> dict:
        """Read configuration from ini file and return content as dict (sections)."""
        config_parser = RawConfigParser(allow_no_value=True, interpolation=None)
        config_parser.optionxform = str
        # All option names are passed through the optionxform() method. Its default implementation converts option names to lower case.
        # That's because this module parses Windows INI files which are expected to be parsed case-insensitively.
        config_parser.read(str(App.resolve_path(path)), encoding=App.ENCONDING)
        return config_parser._sections
        # if interpolation == True for ConfigParser then use get(key, raw=True) as shown bellow:
        # return dict((section, dict((key, config_parser[section].get(key, raw=True)) for key in config_parser[section].keys())) for section in config_parser.sections())

    @staticmethod
    def merge_config(main_dict: dict, default_dict: dict) -> dict:
        """
        Merge two dictionaries.

        if there is no key in @main_dict, it is added from @default_dict as shown in doctest below:
        >>> merged_dict = App.merge_config({'a':{1:1,2:2},'b':{10:10}}, {'a':{1:-1, 3:3}, 'c':{100:100}})
        >>> dict(sorted(dict((k, dict(sorted(v.items()))) for k, v in merged_dict.items()).items()))
        {'a': {1: 1, 2: 2, 3: 3}, 'b': {10: 10}, 'c': {100: 100}}
        """
        # return dict((section, dict((*list(default_dict.get(section, {}).items()), *list(main_dict.get(section, {}).items()))))
        #             for section in set(main_dict) | set(default_dict))
        return dict((section, default_dict.get(section, {}) | main_dict.get(section, {}))  # https://www.python.org/dev/peps/pep-0584/ dict union in python version 3.9
                    for section in set(main_dict) | set(default_dict))

    @classmethod
    def setup_logging(cls, lcfg: dict) -> None:
        """Apply settings specified in Logging config section [lcfg]."""
        logging.basicConfig(**dict((key.replace('BASE_CONFIG_', '').lower(), lcfg[key]) for key in lcfg.keys() if type(key) == str and key.startswith('BASE_CONFIG_') and lcfg[key]))
        if lcfg['FILE_CFG'] and (file_cfg_path := cls.resolve_path(lcfg['FILE_CFG'])):
            if file_cfg_path.suffix.lower() == '.yml':
                with open(str(file_cfg_path), 'rt') as file_cfg:
                    config_dict_yaml = yaml.safe_load(file_cfg.read())
                    logging.config.dictConfig(config_dict_yaml)
            else:
                logging.config.fileConfig(str(file_cfg_path), disable_existing_loggers=True)
        cls.__logger_name = {"__name__": __name__, "": None}.get(lcfg['LOGGER_NAME'], lcfg['LOGGER_NAME'])
        cls.__logger = logging.getLogger(cls.__logger_name)

    @classmethod
    def init(cls, config_path: str) -> None:
        """Initialize application properties (App.logger, App.cfg) by resolving config settings."""
        if sys.version_info < cls.REQUIRED_PYTHON_VER:
            raise RuntimeError(f"This package requres Python {cls.REQUIRED_PYTHON_VER}+")
        config = cls.load_config(cls.resolve_path(config_path))
        config = cls.merge_config(config, cls.__default_config)
        cls.setup_logging(config['Logging'])
        # make spme basic validations
        if not cls.is_version_applicable(config['App']['VERSION']):
            raise ValueError(f'Config version [{config["App"]["Version"]} isn"t applicable. Current version = {cls.__default_config["App"]["Version"]}')
        for path, error_msg in [(config['Logs']['DIR'], 'Logs directory doesn"t exist.'),
                                (config['Report']['TEMPLATE_FILE_PATH'], 'Report template file doesn"t exist.')]:
            path = App.resolve_path(path)
            if not path.exists() or not os.access(path, os.F_OK):
                raise RuntimeError(f'App can"t run due to an error - {error_msg} {str(path)}')
        cls.__config = config

    @classmethod
    def is_version_applicable(cls, version: str) -> bool:
        """Return true if major and minor values are the same for input version and inner __version__."""
        return version.split(".")[:-1] == cls.__default_config['App']['VERSION'].split(".")[:-1]


def main(app=App) -> int:
    """
    main

    Args:
        App: application settings class

    Returns:
        -1 (or Exception raised) - smt unexpected
        0 - ok
        1 - no logs
        2 - report exists
    """
    cfg = app.cfg
    FileInfo = cs.namedtuple("FileInfo", ['path', 'cdt', 'ext'])
    RequestInfo = cs.namedtuple("RequestInfo", ['uri', 'time'])

    def actual_log_info(log_cfg) -> FileInfo:
        """
        Look up files with [log_cfg.FILE_NAME_PREFIX] base name prefix in [log_cfg.DIR] directory.

        Args:
            log_cfg (AppConfig.Logs): with properties [DIR ('logs'), FILE_NAME_PREFIX ('nginx-access-ui.log-'), FILE_NAME_DATE_FORMAT ('%Y%m%d')]

        Returns:
            FileInfo: (path: Path, cdt: datetime, ext: str) or None if not found
        """
#       (logs := sorted(list(f for f in log_dir.glob(f"{config['Logs']['FILE_PREFIX']}*") if f.is_file()),
#                     key = lambda s: datetime.strptime(wosuffixes(s.name[len(config['Logs']["FILE_PREFIX"]):]), config['Logs']['FILE_DATE_FORMAT']).date(),
#                     reverse=True)):
        file_info = FileInfo(None, datetime.min, None)
        for file_path in Path(app.resolve_path(log_cfg.DIR)).iterdir():
            if file_path.is_file() and (file_path.name.startswith(log_cfg.FILE_NAME_PREFIX) if log_cfg.FILE_NAME_PREFIX else True):
                ext = ".".join(file_path.name[len(log_cfg.FILE_NAME_PREFIX):].split('.')[log_cfg.FILE_NAME_DATE_FORMAT.count(".")+1:])
                cdt = file_path.name.lstrip(log_cfg.FILE_NAME_PREFIX).rstrip(f'.{ext}')
                with suppress(ValueError, TypeError):
                    cdt = datetime.strptime(cdt, log_cfg.FILE_NAME_DATE_FORMAT)
                if type(cdt) != datetime:
                    continue
                if cdt > file_info.cdt:
                    file_info = FileInfo(file_path, cdt, ext)
        return file_info if file_info.path else None

    def generate_report_file_name(report_cfg, log_file_info: FileInfo) -> Path:
        """
        Generate report's file name as follows...

        1. In [report_cfg.DIR] directory
        2. File name:
            a. starts with [report_cfg.FILE_NAME_PREFIX]
            b. + log_file_info.cdt.strftime([report_cfg.FILE_NAME_DATE_FORMAT])
            c. + [report_cfg.FILE_NAME_EXT] ext or template ext if None

        Args:
            report_cfg (AppConfig.Report): Report config object with keys [DIR, FILE_NAME_PREFIX, FILE_NAME_DATE_FORMAT, FILE_NAME_EXT]
            log_file_info (FileInfo): contains .cdt property

        Returns:
            Path: valid path for report file
        """
        report_path = app.resolve_path(report_cfg.DIR)
        report_path.mkdir(parents=True, exist_ok=True)
        return report_path.joinpath(f'{report_cfg.FILE_NAME_PREFIX}{log_file_info.cdt.strftime(report_cfg.FILE_NAME_DATE_FORMAT)}{report_cfg.FILE_NAME_EXT if report_cfg.FILE_NAME_EXT else Path(report_cfg.TEMPLATE_FILE_PATH).suffix}')

    def log_lines(log_file_info: FileInfo, mode='rt', encoding=app.ENCONDING) -> str:
        """Return generator of [log_file_info.path] file lines."""
        with {'gz': gzip.open, 'bz2': bz2.open}.get(log_file_info.ext, open)(str(log_file_info.path), mode, encoding=encoding) as log:
            for line in log:
                yield line.rstrip("\n")

    def get_request_info(log_line: str, log_line_parser) -> RequestInfo:
        if (groups := log_line_parser.search(log_line)) and (groupdict := groups.groupdict()):
            with suppress(ValueError):
                return RequestInfo(uri=str.lower(groupdict['request_url']), time=float(groupdict['request_time']))
            # return RequestInfo(*(fn(arg) for fn, arg in zip([str.lower, float], itemgetter('request_url', 'request_time')(groups.groupdict()))))
        return None

    # process actual log file info
    log_file_info = actual_log_info(cfg.Logs)
    if not log_file_info:
        app.logger.info(f'There are no log files in log directory {cfg.Logs.DIR} with specified prefix {cfg.Logs.FILE_NAME_PREFIX} and dt format {cfg.Logs.FILE_NAME_DATE_FORMAT}.')
        return 1
    app.logger.debug(log_file_info)

    # check report file for existence
    report_file_path = generate_report_file_name(cfg.Report, log_file_info)
    if report_file_path.exists():
        app.logger.info(f'Report file [{report_file_path}] has been already created earlier.')
        return 2
    app.logger.debug(report_file_path)

    # parse logs
    log_line_count = 0
    total_request_time = 0
    mismatched_line_numbers = []
    stat_requests = cs.defaultdict(list)
    log_line_parser = re.compile(cfg.Logs.LINE_FORMAT, re.IGNORECASE)
    for log_line_count, log_line in enumerate(log_lines(log_file_info)):
        # Log line example:
        # '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390\n'
        if request_info := get_request_info(log_line, log_line_parser):
            total_request_time += request_info.time
            stat_requests[request_info.uri].append(request_info.time)
        else:
            mismatched_line_numbers.append(log_line_count)
    if mismatched_line_numbers:
        app.logger.debug(f'Mismatched line numbers in log file {log_file_info.path}:\n{" ".join(map(str,mismatched_line_numbers))}')
    if cfg.Logs.UNMATCHED_LINE_LIMIT and (float(cfg.Logs.UNMATCHED_LINE_LIMIT) < len(mismatched_line_numbers) / log_line_count):
        app.logger.error(f'Mismatch limit has been exceeded. Parsing errors count = {len(mismatched_line_numbers)}.')
        return -1

    # prepare parsed logs statistics
    list_requests = []
    for url, times in stat_requests.items():
        times_sum = sum(times)
        times_count = len(times)
        list_requests.append({
            'count': times_count,   # count - сколько раз встречается URL, абсолютное значение
            'time_sum': round(times_sum, app.ROUND_NDIGITS),  # time_sum - суммарный $request_time для данного URL'а, абсолютное значение
            'count_perc': round(100 * times_count / (log_line_count - len(mismatched_line_numbers)), app.ROUND_NDIGITS),    # count_perc - сколько раз встречается URL, в процентнах относительно общего числа запросов
            'time_perc': round(100 * times_sum / total_request_time, app.ROUND_NDIGITS),    # time_perc - суммарный $request_time для данного URL'а, в процентах относительно общего $request_time всех запросов
            'time_avg': round(times_sum / times_count, app.ROUND_NDIGITS),    # time_avg - средний $request_time для данного URL'а
            'time_max': max(times),  # time_max - максимальный $request_time для данного URL'а
            'time_med': round(median(times), app.ROUND_NDIGITS),  # time_med - медиана $request_time для данного URL'а
            'url': url,
            })

    # sort by $time_sum desc and take first Report.REPORT_SIZE records
    list_requests = sorted(list_requests, key=itemgetter('time_sum'), reverse=True)[:int(cfg.Report.REPORT_SIZE)]

    # open report template and read content
    report_content = ""
    with open(cfg.Report.TEMPLATE_FILE_PATH, 'rt', encoding=app.ENCONDING) as report_template_file:
        report_content = report_template_file.read()
    report_content = Template(report_content).safe_substitute(table_json=json.dumps(list_requests))

    # save fullfilled template content to report file
    with open(report_file_path, 'wt', encoding=app.ENCONDING) as report_file:
        report_file.write(report_content)

    app.logger.info(f'Report has been successfully created and saved to file: {str(report_file_path)}')
    return 0


if __name__ == "__main__":
    try:
        args = docopt(__doc__, version=__version__)
        if args["-i"]:
            App.save_config(args["--config"])
        elif args["-v"]:
            print(f'{args=}')
            import doctest
            doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
        else:
            App.init(args["--config"])
            main(App)
    except DocoptExit as exc:
        App.logger.error(f'Not a valid usage pattern.\n{__doc__}')
    except BaseException:   # do not use bare 'except' - pycodestyle(E722)
        App.logger.exception("Oops...", exc_info=True)
