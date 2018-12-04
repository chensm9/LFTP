def log_info(*args):
  s = ">>> "
  for i in range(len(args)):
    s = s + str(args[i])
  print('\033[32m%s' % s)

def log_warn(*args):
  s = ">>> "
  for i in range(len(args)):
    s = s + str(args[i])
  print('\033[33m%s' % s)

def log_error(*args):
  s = ">>> "
  for i in range(len(args)):
    s = s + str(args[i])
  print('\033[31m%s' % s)