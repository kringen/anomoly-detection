# From https://gist.github.com/kyrcha/974f662d988906023d20cadf22a8a88e

from multiprocessing import Pool
import redis
import math
import json
from random import seed
from random import gauss

# Atomic operations
def sum(x):
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.incrbyfloat('sum', x)

# transactional operations using EVAL
def welford(x):
    r = redis.Redis(host='localhost', port=6379, db=0)
    pipe = r.pipeline()
    running(keys=['aggregate'], args=[x], client=pipe)
    pipe.execute()

if __name__ == '__main__':
    # create a sequence of numbers following a normal distribution
    # of mean 0 and 1 standard deviation
    seed(1)
    sequence = [gauss(0,1) for i in range(1000)]
    # connect to redis and initialize
    rmain = redis.Redis(host='localhost', port=6379, db=0)
    rmain.set('sum', 0)
    rmain.set('aggregate', '{ "n": "0", "m": "0", "m2": "0" }')
    # Welford's online algorithm
    # https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_online_algorithm
    lua_script = """
        local aggregate = redis.call('get',KEYS[1])
        local decode = cjson.decode(aggregate)
        local n = decode['n']
        n = n + 1
        local m = decode['m']
        local m2 = decode['m2']
        local delta = ARGV[1] - m
        m = m + delta/n
        m2 = m2 + delta * (ARGV[1] - m)
        decode['n'] = n
        decode['m'] = m
        decode['m2'] = m2
        local encoded = cjson.encode(decode)
        redis.call('set', KEYS[1], encoded)
    """
    running = rmain.register_script(lua_script)
    p = Pool(100) # create a pool of 100 threads
    p.map(sum, sequence) # calculate the sum
    p.map(welford, sequence) # calculate running mean and variance or standard deviation
    print('sum: ' + str(rmain.get('sum')))
    result = json.loads(rmain.get('aggregate'))
    print('count: ' + str(result['n']))
    print('mean: ' + str(result['m']))
    print('std: ' + str(math.sqrt(result['m2']/result['n'])))