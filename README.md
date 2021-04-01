# <b>log anylyzer</b>
<i>otus python pro courses: lesson 1</i>

this python script finds actual nginx's log, parses file, collects time and frequency statistics of requests for each url and writes out report according to specified template. All settings are set in the config file.

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
VERSION = 0.1.0

[Report]
DIR = reports
REPORT_SIZE = 1000

[Logs]
DIR = logs
FILE_NAME_PREFIX = nginx-access-ui.log-
FILE_NAME_DATE_FORMAT = %Y%m%d
LINE_FORMAT = ^...(?P<request_url>...*)...(?P<request_time>...*)...$ 

[Logging]
LOGGER_NAME = \__name__ | some.name | [empty]        - \__name__ -> loggers = \__main__ | module.name, <empty> -> loggers = root 
BASE_CONFIG_FORMAT = ...%(message)s... | [empty]
BASE_CONFIG_DATEFMT = %Y.%m.%d %H:%M:%S | [empty]
BASE_CONFIG_LEVEL = NOSET | DEBUG | WARN | ERROR | CRITICAL | [empty]
BASE_CONFIG_FILENAME = log_analyzer.log | [empty]   - if <empty> then no logging to file
BASE_CONFIG_FILEMODE = w | a | [empty]
FILE_CFG = logging.ini | logging.yaml | [empty]     - .ext = .ini | .yaml
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