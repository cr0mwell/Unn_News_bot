FIREFOX_PATH = r'C:\FirefoxPortable\App\Firefox64\firefox.exe'
PROJ_PATH    = r'D:\python\PyCharmProjects\UnnParserBot'

COLUMNS = {'politics' : 'політика',
           'economics': 'економіка',
           'agronews' : 'економіка',
           'kiev'     : 'суспільство',
           'society'  : 'суспільство',
           'health'   : 'суспільство',
           'criminal' : 'кримінал',
           'lite'     : 'позитив',
           'world'    : 'міжнародні новини',
           'tech'     : 'технології',
           'sport'    : 'спорт',
           'culture'  : 'культура'}

COLS_TO_NUM = {'економіка'        : 0,
               'кримінал'         : 1,
               #'культура'         : 2,
               'міжнародні новини': 2,
               #'позитив'          : 4,
               'політика'         : 3,
               'спорт'            : 4,
               'суспільство'      : 5,
               #'технології'       : 8
               }

NUM_TO_COLS = {0: 'економіка',
               1: 'кримінал',
               #2: 'культура',
               2: 'міжнародні новини',
               #4: 'позитив',
               3: 'політика',
               4: 'спорт',
               5: 'суспільство',
               #8: 'технології',
               9: 'hot'
               }

NUM_TO_ICONS = {0: '💰',
                1: '👮‍',
                2: '🌏',
                3: '🎩',
                4: '⚽',
                5: '👨‍👩‍👧',
                9: '🔥'}

WEEKDAYS = {0: 'Понеділок',
            1: 'Вівторок',
            2: 'Середа',
            3: 'Четвер',
            4: 'Пятниця',
            5: 'Субота',
            6: 'Неділя'}

MONTHS = {1: 'січня',
          2: 'лютого',
          3: 'березня',
          4: 'квітня',
          5: 'травня',
          6: 'червня',
          7: 'липня',
          8: 'серпня',
          9: 'вересня',
          10: 'жовтня',
          11: 'листопада',
          12: 'грудня'}
