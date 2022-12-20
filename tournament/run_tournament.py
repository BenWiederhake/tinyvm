#!/usr/bin/env python3

import os

VMS_DIR = "../vms/connect4/"
OUTPUT_DIR = "pages/"


class VM:
    def __init__(self, name, )


def change_to_this_files_dir():
    os.chdir(os.dirname(__file__))


def collect_vms():
    vms = []
    for filename in os.listdir():
        
    raise NotImplementedError()


def run_match(vm_one, vm_two):
    raise NotImplementedError()


def emit_match(vm_one, vm_two):
    raise NotImplementedError()


def emit_vm_summary(vm, all_vms):
    raise NotImplementedError()


def emit_total_summary(all_vms):
    raise NotImplementedError()


def run():
    change_to_this_files_dir()
    if not os.path.exists(OUTPUT_DIR):
        print(f"Directory {OUTPUT_DIR} doesn't exist. Creating an empty directory.")
        os.mkdir(OUTPUT_DIR)

    vms = collect_vms()
    for vm_one in vms:
        for vm_two in vms:
            run_match(vm_one, vm_two)
            emit_match(vm_one, vm_two)
    for vm in vms:
        emit_vm_summary(vm, vms)
    emit_total_summary(vms)


if __name__ == "__main__":
    run()
