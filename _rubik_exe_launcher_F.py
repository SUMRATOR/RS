import multiprocessing

from rubik_studio.main import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
