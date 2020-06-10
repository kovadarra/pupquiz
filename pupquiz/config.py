from pkg_resources import resource_filename
import PySimpleGUI as sg
import os
import ujson


def data_path(*args):
    return os.path.join(os.getenv('APPDATA'), 'pupquiz', *args)


cfg = {
    'app-icon': resource_filename('pupquiz.resources', 'icon.ico'),
    'color-text': '#f0eff4',
    'color-select-info-guide': '#f0eff4',
    'color-background': '#111111',
    'color-input-text': '#f0eff4',
    'color-input-background': '#3d2645',
    'color-button-text': '#f0eff4',
    'color-button-background': '#832161',
    'color-info-incorrect': '#da4167',
    'color-info-correct': '#f0eff4',
    'color-info-greet': '#f0eff4',
    'color-info-new-word': '#f0eff4',
    'color-info-translation-opened': '#f0eff4',
    'select-info-guide-width': 4,
    'select-info-guide-height': 59,
    'patt-set': r'(?i)^(?P<set>.+\\)(?P<img>.+\.(jpg|gif|png))$',
    'patt-gif-loop-pause': r'(?i)(?<!p)\.gif$',
    'patt-vocab-word': r'(?m)^(?P<q>.+)\n[^\S\n]*~ (?P<a>.+)',
    'patt-vocab-word-subdivider': r'<br>|<i>.*?</i>',
    'patt-vocab-file': r"""(?ms)^title: "(?P<title>.+?)"$.+?^content: '''(?P<contents>.+?^)'''""",
    'vocab-file-types': [['Vocabulary Files', '*.cson']],
    'common-sets': [data_path('Default Assets')],
    'gif-pause-duration': 1.2,
    'pad-top-status': 150,
    'image-max-width': 400,
    'image-max-height': 500,
    'control-border-width': 0,
    'font': '"Berlin Sans FB" 13',
    'thumbnail-placeholder-color-hover': '#626262',
    'thumbnail-placeholder-color-default': '#454545',
    'thumbnail-placeholder-width': 10,
    'thumbnail-size': 128,
    'thumbnail-sample': 4,
    'thumbnail-font-file': 'BRLNSR.TTF',
    'thumbnail-font-size': 16,
    'thumbnail-font-color': '#f0eff4',
    'thumbnail-text-stroke-color': '#000000',
    'thumbnail-text-stroke-size': 1,
    'thumbnail-border-color': '#333333',
    'thumbnail-border-size': 1,
    'thumbnail-undone-brightness': 0.75,
    'thumbnail-undone-saturation': 0.4,
    'thumbnail-undone-blur-radius': 3,
    'translate-url': 'https://translate.google.com/#auto/en/{}',
    'locale': ['Pup Quiz', 'Click on a vocabulary to quiz for it.\nAdd a vocabulary by selecting an empty slot.\nDelete a vocabulary with a right-click.', '{} - Pup Quiz', 'Welcome to Pup Quiz!', 'Correct! {:.2f}%', '{}', 'Added to word stock', 'Got it!', 'Submit', 'Translate', 'Translation opened', 'Reset', 'Menu', 'Are you sure you want to delete "{}"?', 'Are you sure you want to reset progress on "{}"?']
}


CFG_PATH = data_path('config-user.json')


if not os.path.isdir(data_path()):
    os.mkdir(data_path())

if not os.path.isdir(data_path('Default Assets')):
    from zipfile import ZipFile
    from pkg_resources import resource_stream
    with ZipFile(resource_stream('pupquiz.resources', 'default-assets.zip'), 'r') as f:
        f.extractall(data_path())


if not os.path.isfile(data_path('config-default.json')):
    with open(data_path('config-default.json'), 'w') as f:
        ujson.dump(cfg, f, indent=4)  # for reference
try:
    with open(CFG_PATH, 'r') as f:
        cfg.update(ujson.load(f) or {})  # apply user preference
except FileNotFoundError:
    with open(CFG_PATH, 'w') as f:
        f.write('{\n}')


sg.set_global_icon(cfg['app-icon'])
sg.theme_background_color(cfg['color-background'])
sg.theme_element_background_color(cfg['color-background'])
sg.theme_text_color(cfg['color-text'])
sg.theme_text_element_background_color(cfg['color-background'])
sg.theme_input_text_color(cfg['color-input-text'])
sg.theme_input_background_color(cfg['color-input-background'])
sg.theme_button_color(
    (cfg['color-button-text'], cfg['color-button-background']))
sg.theme_border_width(cfg['control-border-width'])

CFG_APPNAME, CFG_SELECT_INFO, CFG_APPNAME_SES, CFG_GREET, CFG_CORRECT, CFG_INCORRECT, CFG_ADDWORD, CFG_NEWWORD, CFG_GUESS, CFG_TRANSLATE, CFG_TRANSLATE_OPENED, CFG_RESET, CFG_MENU, CFG_CONFIRM_DELETE, CFG_CONFIRM_RESET = cfg[
    'locale']
