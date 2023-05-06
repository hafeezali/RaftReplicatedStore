from graphlib import TopologicalSorter
import math

def get_log_key(log, test=False):
    if test:
        return log['key']
    return log['clientid'] + '_' + log['sequence_number']

def recover_durability_log(dura_logs, f, test=False):
    dura_log_pos_map = list()
    dura_log_freq = dict()
    dura_log_key_map = dict()
    for idx in range(len(dura_logs)):
        log = dura_logs[idx]
        log_position = dict()
        for idx in range(len(log)):
            entry = log[idx]
            key = get_log_key(entry, test)
            if key in dura_log_freq:
                dura_log_freq[key] += 1
            else:
                dura_log_freq[key] = 1
            if key not in dura_log_key_map:
                dura_log_key_map[key] = entry
            log_position[key] = idx
        dura_log_pos_map.append(log_position)
    graph = dict()
    for key in dura_log_freq.keys():
        if dura_log_freq[key] >= math.ceil(f/2) + 1:
            graph[key] = set()
    nodes = list(graph.keys())
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i != j:
                i_before_j = 0
                i_but_not_j = 0
                for log_pos in dura_log_pos_map:
                    if nodes[i] in list(log_pos.keys()) and nodes[j] in list(log_pos.keys()):
                        if log_pos[nodes[i]] < log_pos[nodes[j]]:
                            i_before_j += 1
                    elif nodes[i] in log_pos.keys():
                        i_but_not_j += 1
                if i_before_j + i_but_not_j >= math.ceil(f/2) + 1:
                    graph[nodes[i]].add(nodes[j])
    ts = TopologicalSorter(graph)
    new_dura_order = tuple(ts.static_order())
    result_dura_log = list()
    for key in new_dura_order:
        result_dura_log.append(dura_log_key_map[key])
    result_dura_log.reverse()
    return result_dura_log

