import sys

def classify(col):
    col = col.strip()
    if not col:
        return col  # 빈 칸은 원본 유지

    # 타입과 이름 분리 (마지막 토큰이 변수명)
    tokens = col.split()
    if not tokens:
        return col

    name = tokens[-1].lstrip('*')  # 포인터 * 제거
    full = col

    if 'char *' in full or "char*" in full:  return 'ARG_STR'
    if 'flag' in name or 'flg' in name:       return 'ARG_FLAGS'
    if 'umode_t' in full:                     return 'ARG_MODE'
    if name == 'fd':                          return 'ARG_FD'
    if 'pid_t' in full:                       return 'ARG_PID'
    if 'size_t' in full:                      return 'ARG_SIZE'
    if 'off_t' in full:                       return 'ARG_OFFSET'
    if 'struct' in full and '*' in full:      return 'ARG_STRUCT_PTR'
    if 'void *' in full:                      return 'ARG_PTR'
    if 'void' in full:                      return 'ARG_NONE'
    if 'fildes' in name or 'newfd' in name or 'oldfd' in name: return 'ARG_FD'
    if 'uid_t' in full:                return 'ARG_UID'
    if 'gid_t' in full:                return 'ARG_GID'
    if name == 'sig' or 'sigset' in full or 'sighandler' in full: return 'ARG_SIGNAL'
    if 'mask' in name:                 return 'ARG_FLAGS'
    if '*' in full:                    return 'ARG_PTR'   # 포인터는 다 ARG_PTR
    return 'ARG_INT'                   # 마지막은 다 ARG_INT

with open(sys.argv[1]) as f:
    for line in f:
        cols = line.rstrip('\n').split('|')
        result = '|'.join(classify(c) for c in cols)
        print(result)