# <b>log anylyzer</b>
<i>otus python pro courses: lesson 1</i>

this python script finds actual nginx's log, parses it and collects time / frequency statistics of requests per url and writes out report according to specified template.

## Usage: 
```
log_analyzer.py [options]

Options:
    -c FILE_INI --config=FILE_INI   Config file [default: log_analyzer.ini]
    -i                              Write default ini config settings to FILE_INI
    -v                              Run doctests
    -h  --help                      Show this screen.
    --version                       Show version.
```
## Config files example:
### log_analyzer.ini 
```
[App]
VERSION = v0.1.0

[Report]
DIR = reports
FILE_NAME_PREFIX = nginx-access-ui.report-
FILE_NAME_DATE_FORMAT = %Y%m%d
REPORT_SIZE = 500
TEMPLATE_FILE_PATH = reports/report.html

[Logs]
DIR = logs
FILE_NAME_PREFIX = nginx-access-ui.log-
FILE_NAME_DATE_FORMAT = %Y%m%d
LINE_FORMAT = ^(?P<remote_addr>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})\s+\S+\s+\S+\s+\[(?P<time_local>.+)\]\s+"(?P<request_method>[A-Z]+)\s+(?P<request_url>[\w\.\-\/]+)(?P<request_params>\?[\S]*)*\s+(?P<protocol>.*?)"\s+(?P<status>\d{3})\s+(?P<body_bytes_sent>\d+)\s+\S+\s+"(?P<http_user_agent>.*?)".*?(?P<request_time>[\d\.]*)$
UNMATCHED_LINE_LIMIT = 0.1

[Logging]
LOGGER_NAME = __name__
FILE_CFG = logging.ini
```
- default config:
```
    {
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
```

### logging config
__.ini__
```
[loggers]
keys=root,__main__,log_anylizer

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=consoleFormatter,fileFormatter

[logger_root]
level=NOTSET
handlers=consoleHandler

[logger___main__]
level=DEBUG
handlers=consoleHandler,fileHandler
qualname=__main__
propagate=0

[logger_log_anylizer]
level=DEBUG
handlers=fileHandler
qualname=log_anylizer

[handler_consoleHandler]
class=StreamHandler
level=WARNING
formatter=consoleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=FileHandler
level=DEBUG
formatter=fileFormatter
args=('log_anylizer.log','w')

[formatter_consoleFormatter]
format=[%(asctime)s] %(name)s %(levelname).1s %(message)s
datefmt=%Y.%m.%d %H:%M:%S

[formatter_fileFormatter]
format=[%(asctime)s] %(name)s (%(filename)s).%(funcName)s(%(lineno)d) %(levelname).1s %(message)s
datefmt=%Y.%m.%d %H:%M:%S
```
__.yml__
```
version: 1
disable_existing_loggers: true
formatters:
  console:
    format: "[%(asctime)s] %(name)s %(levelname).1s %(message)s"
    datefmt: "%Y.%m.%d %H:%M:%S"
  file:
    format: "[%(asctime)s] %(name)s (%(filename)s).%(funcName)s(%(lineno)d) %(levelname).1s %(message)s"
    datefmt: "%Y.%m.%d %H:%M:%S"
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: console
    stream: ext://sys.stdout
  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: file    
    filename: log_anylizer.log
    encoding: utf8
    mode: w  
loggers:
  __main__:
    level: DEBUG
    handlers: [console, file]
    propagate: no
  log_analyzer:
    level: DEBUG
    handlers: [file]
    propagate: yes
root:
  level: NOTSET
  handlers: [console]
  propagate: no  
```