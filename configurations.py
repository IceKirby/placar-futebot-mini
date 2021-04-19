#!/usr/bin/python
from configparser import ConfigParser
from configupdater import ConfigUpdater

def get_config(filename='config.ini', section='SETTINGS'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename, encoding='utf-8')

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db
    
def save_setting(property, value, section='STORE', filename='config.ini'):
    updater = ConfigUpdater()
    updater.read(filename)
    
    updater[section][property].value = value
    updater.update_file()