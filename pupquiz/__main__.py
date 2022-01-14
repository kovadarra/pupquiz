if __name__ == '__main__':
    # import matplotlib
    # matplotlib.use('Agg')
    # import matplotlib.pyplot as plt
    import PySimpleGUI as sg
    from pupquiz.config import CFG_APPNAME
    from sys import argv
    if '--debug' in argv:
        from pupquiz.session import main_loop
        main_loop()
    else:
        try:
            from pupquiz.session import main_loop
            main_loop()
        except Exception as e:
            sg.popup_error(e, title=CFG_APPNAME)
            import sys
            sys.exit(1)
