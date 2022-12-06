# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""
Miscellaneous helpers
=====================
**Author**: `Federico Peccia <https://fPecc.github.io/>`_
"""

import numpy as np
import pathlib
from .environment import Environment

import abc
import collections
import matplotlib
import matplotlib.pyplot as plt  # pylint: disable=g-import-not-at-top
import PIL.Image as Image
import PIL.ImageColor as ImageColor
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
import six
from six.moves import range
from six.moves import zip
import tensorflow.compat.v1 as tf
from typing import List, Tuple


env = Environment.instance()


def create_header_file(
    name: str,
    section: str,
    tensor_name: str,
    tensor_data: np.ndarray,
    output_path: str,
    debug: bool = False,
    weights: bool = None,
):
    """This function generates a header file containing the data from the numpy array provided.

    Args:
        name (str): Header file name
        section (str): section to assign the generated variable
        tensor_name (str): name for the generated variable
        tensor_data (np.ndarray): data to fill the variable with
        output_path (str): output path where the header file will be generated
        debug (bool, optional): enable debug. Defaults to False.
        weights (bool, optional): For debug purposes. Defaults to None.
    """
    file_path = pathlib.Path(f"{output_path}/" + name).resolve()
    # Create header file with npy_data as a C array
    raw_header_path = file_path.with_suffix(".h").resolve()
    raw_source_path = file_path.with_suffix(".c").resolve()

    if tensor_data.dtype == np.float32:
        type = "float"
        align = 32
    elif tensor_data.dtype == np.int8:
        type = "int8_t"
        align = 16
    elif tensor_data.dtype == np.uint8:
        type = "uint8_t"
        align = 16
    elif tensor_data.dtype == np.uint32:
        type = "uint32_t"
        align = 16
    else:
        assert False, "Type %s is not supported!" % tensor_data.dtype

    with open(raw_header_path, "a+") as header_file:
        header_file.write(
            f"#define {tensor_name}_len {tensor_data.size}\n"
            + f"extern {type} {tensor_name}[{tensor_name}_len];\n"
        )

    if not raw_source_path.is_file():
        with open(raw_source_path, "a+") as source_file:
            source_file.write(f"#include <stdint.h>\n")
    with open(raw_source_path, "a+") as source_file:

        source_file.write(
            f'{type} {tensor_name}[] __attribute__((section("{section}"), aligned({align}))) = {{'
            if section
            else f"{type} {tensor_name}[] __attribute__((aligned({align}))) = {{"
        )
        data_hexstr = tensor_data.tobytes().hex()
        flatten = tensor_data.flatten()

        if tensor_data.dtype == np.float32 or tensor_data.dtype == np.uint32:
            for i in range(0, len(flatten)):
                source_file.write(f"{flatten[i]},")
            source_file.write("};\n\n")
        else:
            for i in range(0, len(data_hexstr), 2):
                if flatten[int(i / 2)] < 0:
                    # Special treatment to generate negative numbers correctly!
                    data_hexstr_2comp = (
                        (~int(flatten[int(i / 2)]) + 1).to_bytes(length=1, byteorder="big").hex()
                    )
                    source_file.write(f"-0x{data_hexstr_2comp}")
                else:
                    source_file.write(f"+0x{data_hexstr[i:i+2]}")
                if i != (len(flatten) - 1) * 2:
                    source_file.write(",")
            source_file.write("};\n\n")

        if debug:
            source_file.write("/*\n")
            for n in range(tensor_data.shape[0]):
                for ch in range(tensor_data.shape[3]):
                    source_file.write("Channel %i:\n" % ch)
                    for row in range(tensor_data.shape[1]):
                        for col in range(tensor_data.shape[2]):
                            source_file.write(f"{tensor_data[n][row][col][ch]}\t")
                        source_file.write("\n")
            source_file.write("*/\n")

            if weights is not None:
                source_file.write("/*\n")
                for o_ch in range(weights.shape[3]):
                    source_file.write("Output channel %i:\n" % o_ch)
                    for i_ch in range(weights.shape[2]):
                        source_file.write("Input channel %i:\n" % i_ch)
                        for row in range(weights.shape[0]):
                            for col in range(weights.shape[1]):
                                source_file.write(f"{weights[row][col][i_ch][o_ch]}\t")
                            source_file.write("\n")
                source_file.write("*/\n")


def get_divisors(x: int) -> List[int]:
    """Gets all the numbers that perfectly divide x

    Args:
        x (int): Number to divide

    Returns:
        List[int]: list of divisors
    """
    divs = []
    for i in range(1, x + 1):
        if x % i == 0:
            divs.append(i)
    return divs


def get_greater_div(x, limit: int = None):
    """Gets the greater divisor for all x

    Args:
        x: _description_
        limit (int, optional): Max greater divisor to return. Defaults to None.

    Returns:
        int: Greater divisor
    """

    limit = env.DIM if limit == None else limit

    if isinstance(x, int):
        elements = [x]
    elif isinstance(x, list):
        elements = x
    else:
        assert False, "type of x not supported!"

    divisors = []
    for element in elements:
        divs = get_divisors(element)
        filtered = filter(lambda d: d <= limit, divs)
        divisors.append(filtered)

    return max(set.intersection(*map(set, divisors)))
