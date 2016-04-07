from pprint import pprint


def checkout(files):
    print 'Checkout {} files :'.format(len(files))
    pprint(files)


def submit(files):
    print 'Submit {} files :'.format(len(files))
    pprint(files)


def revert(files):
    print 'Revert {} files :'.format(len(files))
    pprint(files)
