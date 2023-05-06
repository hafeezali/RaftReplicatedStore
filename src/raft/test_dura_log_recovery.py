from dura_log_recovery import recover_durability_log

def test1(logs):
    dura_logs = recover_durability_log(logs, 2, test=True)
    assert dura_logs == [{'key': 'b'}, {'key': 'a'}, {'key': 'c'}, {'key': 'd'}]

def test2(logs):
    dura_logs = recover_durability_log(logs, 2, test=True)
    assert dura_logs == [{'key': 'a'}, {'key': 'b'}, {'key': 'c'}]

if __name__ == '__main__':
    logs = list()

    dura_1 = [{'key':'b'}, {'key':'a'}, {'key':'c'}, {'key':'d'}]
    dura_2 = [{'key':'b'}, {'key':'a'}, {'key':'c'}, {'key':'d'}]
    dura_3 = [{'key':'a'}, {'key':'b'}, {'key':'c'}]
    dura_4 = []

    # Example 7(i) from paper
    logs.append(dura_1)
    logs.append(dura_2)
    logs.append(dura_3)
    test1(logs)
    
    # Example 7(ii) from paper
    logs.clear()
    logs.append(dura_1)
    logs.append(dura_3)
    logs.append(dura_4)
    test2(logs)