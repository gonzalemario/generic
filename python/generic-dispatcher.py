import argparse
import asyncio
import json
import logging
import sys


failed_commands = []
process_limit = asyncio.Semaphore(3)

async def stream_stdout(stream, fname):
    stdout_log = open("output-"+fname, "a")
    while True:
        line = await stream.readline()
        if not line: break
        stdout_log.write(line.decode())
    stdout_log.close()


async def launch(command, name_id):
    logging.info('Running: '+command)
    process = await asyncio.create_subprocess_shell(command,
            limit = 1024 * 128,  # 128 KiB
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
            )

    await asyncio.wait( (stream_stdout(process.stdout, name_id),) )

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        result = {'cmd': command, 'code' : process.returncode, 'stdout' : stdout.decode(), 'stderr' : stderr.decode() }
        failed_commands.append(result)


async def prepare_launch(command, name_id):
    async with process_limit:
        return await launch(command, name_id)


async def main(args):
    tasks = []
    for command in args:
        callback = asyncio.ensure_future(prepare_launch(command, "name"))
        tasks.append(callback)
    await asyncio.gather(*tasks)


def process_error_output():
    logging.warning('Please check the logs for these commands')
    for p in failed_commands:
        msg = "I received status code %s after running: %s" % (p['code'], p['cmd'])
        logging.warning(msg)

    return -1


if __name__ == "__main__":
    #TODO: change `procs` by your list of commands you need to run
    procs = []
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(procs))

    if not failed_commands: exit_code = 0
    else:
        exit_code = process_error_output()

    sys.exit(exit_code)

