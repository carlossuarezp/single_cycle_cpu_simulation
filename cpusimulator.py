import pyrtl



i_mem = mem = pyrtl.MemBlock(bitwidth=32, addrwidth=4, name='i_mem', max_read_ports=None, max_write_ports=None, asynchronous=True, block=None)
d_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='d_mem', max_read_ports=None, max_write_ports=None, asynchronous=True, block=None)
rf = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='rf', max_read_ports=None, max_write_ports=None, asynchronous=True, block=None)



# get instructions from i_mem
counter = pyrtl.Register(bitwidth=4)
instr = pyrtl.WireVector(bitwidth=32, name='instr')
instr <<= i_mem[counter]



# INSTRUCTION DECODING LOGIC
op = pyrtl.WireVector(bitwidth=6, name='op')
rs = pyrtl.WireVector(bitwidth=5, name='rs')
rt = pyrtl.WireVector(bitwidth=5, name='rt')
rd = pyrtl.WireVector(bitwidth=5, name='rd')
sh = pyrtl.WireVector(bitwidth=5, name='sh')
func = pyrtl.WireVector(bitwidth=6, name='func')
imm = pyrtl.WireVector(bitwidth=16, name='imm')
addr = pyrtl.WireVector(bitwidth=26, name='addr')
op <<= instr[26:32]
addr <<= instr[0:26]
rs <<= instr[21:26]
rt <<= instr[16:21]
imm <<= instr[0:16]
rd <<= instr[11:16]
sh <<= instr[6:11]
func <<= instr[0:6]



# CONTROL UNIT LOGIC
control_signals = pyrtl.WireVector(bitwidth=10, name='control_signals')
with pyrtl.conditional_assignment:
    # R-types
    with op == 0:
        # ADD
        with func == 0x20:                     
            control_signals |= 0x280
        # AND
        with func == 0x24:
            control_signals |= 0x281
        # SLT
        with func == 0x2a:
            control_signals |= 0x284
    # ADDI
    with op == 0x8:
        control_signals |= 0xa0
    # LUI
    with op == 0xf:
        control_signals |= 0xa2
    # ORI
    with op == 0xd:
        control_signals |= 0xa3
    # LW
    with op == 0x23:
        control_signals |= 0x28
    # SW
    with op == 0x2b:
        control_signals |= 0x30
    # BEQ
    with op == 0x4:
        control_signals |= 0x105
# Declare wires that depart from the control unit
alu_op = pyrtl.WireVector(bitwidth=3, name='alu_op')
mem_to_reg = pyrtl.WireVector(bitwidth=1, name='mem_to_reg')
mem_write = pyrtl.WireVector(bitwidth=1, name='mem_write')
alu_src = pyrtl.WireVector(bitwidth=2, name='alu_src')
regwrite = pyrtl.WireVector(bitwidth=1, name='regwrite')
branch = pyrtl.WireVector(bitwidth=1, name='branch')
reg_dst = pyrtl.WireVector(bitwidth=1, name='reg_dst')
# Extract the relevant signals
alu_op <<= control_signals[0:3]
mem_to_reg <<= control_signals[3]
mem_write <<= control_signals[4]
alu_src <<= control_signals[5:7]
regwrite <<= control_signals[7]
branch <<= control_signals[8]
reg_dst <<= control_signals[9]



# READING FROM THE REGISTER FILE
data0 = pyrtl.WireVector(bitwidth=32, name='data0')    # first operand for the ALU
data1 = pyrtl.WireVector(bitwidth=32, name='data1')    # second operand for the ALU
write_register = pyrtl.WireVector(bitwidth=32, name='write_register')
alu_out = pyrtl.WireVector(bitwidth=32, name='alu_out')    # result from the ALU operation
with pyrtl.conditional_assignment:                  # register writen can be either rd or rt
    with reg_dst == 1:
        write_register |= rd
    with reg_dst == 0:
        write_register |= rt 
data0 <<= rf[rs]
with pyrtl.conditional_assignment:
    with alu_src == 0:
        data1 |= rf[rt]
    with alu_src == 1:
        with alu_op == 3:    # ORI instruction, special case
            data1 |= imm.zero_extended(32)
        with pyrtl.otherwise:
            data1 |= imm.sign_extended(32)



# ALU OPERATIONS
with pyrtl.conditional_assignment:   
    with alu_op == 0:
        alu_out |= data0 + data1
    with alu_op == 1:
        alu_out |= data0 & data1
    with alu_op == 3:
        alu_out |= data0 | data1
    with alu_op == 2:
        alu_out |= pyrtl.shift_left_logical(imm.zero_extended(32),16)
    with alu_op == 4:
        with (data0<data1):
            alu_out |= 1                            
        # else alu_out = 0
        with pyrtl.otherwise:
            alu_out |= 0
    with alu_op == 5:
        alu_out |= data1 - data0



# BRANCHING CONTROL (BEQ instructions)
with pyrtl.conditional_assignment:
    with branch == 1:
        with alu_out == 0:         #(the 2 values on the registers are equal if their subtraction is 0, in which case we branch)
            counter.next |= counter + 1 + imm.sign_extended(32)
        with pyrtl.otherwise:
            counter.next |= counter + 1
    with pyrtl.otherwise:
        counter.next |= counter + 1



# MEMORY CONTROL
mem_out = pyrtl.WireVector(bitwidth=32, name='mem_out')
with pyrtl.conditional_assignment:
    with mem_write == 1:
        d_mem[alu_out] |= rf[rt]
    with mem_write == 0:
        mem_out |= d_mem[alu_out]



# WRITE BACK TO REGISTER FILE
write_back_value = pyrtl.WireVector(bitwidth=32, name='write_back_value')
with pyrtl.conditional_assignment:
    with mem_to_reg == 0:
        write_back_value |= alu_out
    with mem_to_reg == 1:
        write_back_value |= mem_out
with pyrtl.conditional_assignment:
    with regwrite == 1:
        rf[write_register] |= write_back_value



# TEST
test1 = pyrtl.WireVector(bitwidth=32, name='test1')
test1 <<= rf[8]
test2 = pyrtl.WireVector(bitwidth=32, name='test2')
test2 <<= rf[9]
test3 = pyrtl.WireVector(bitwidth=32, name='test3')
test3 <<= d_mem[0]



if __name__ == '__main__':

    # Starting a simulation trace
    sim_trace = pyrtl.SimulationTrace()

    # Initializing the i_mem with a set of instructions
    i_mem_init = {}
    with open('assembled sample instructions.txt', 'r') as fin:
        i = 0
        for line in fin.readlines():
            i_mem_init[i] = int(line, 16)
            i += 1

    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={
        i_mem : i_mem_init
    })

    # Running it for an arbitrarily large number of cycles.
    for cycle in range(500):
        sim.step({})

    # Using render_trace() to debug the code
    sim_trace.render_trace()

    # Printing out the register file or memory for debugging purposes:
    # print(sim.inspect_mem(d_mem))
    # print(sim.inspect_mem(rf))

    # Performing some sanity checks to see if the program worked correctly
    assert(sim.inspect_mem(d_mem)[0] == 10)
    assert(sim.inspect_mem(rf)[8] == 10)    # $v0 = rf[8]
    print('Passed!')