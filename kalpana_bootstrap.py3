if __name__ == '__main__':
    try:
        import kalpana
        kalpana.main()
    except Exception: # and not SystemExit
        from libsyntyche import common
        common.print_traceback()
        input()
