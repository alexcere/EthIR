import opcodes
from utils import getLevel, getKey
import os
from dot_tree import Tree, build_tree

def init():
    global cloned_blocks
    cloned_blocks = []

    global stack_index
    stack_index = {}

# def preprocess_push(block,addresses,blocks_input):
#     push_per_block = {}

#     b_source = blocks_input[block]
#     comes_from = b_source.get_comes_from()
#     # print "COMESFROM"
#     # print comes_from
#     for bl in comes_from:
#         b = blocks_input[bl]
#         instructions = b.get_instructions()
#         m = filter(lambda x: x.split()[0][:-1]=="PUSH",instructions)
#         numbers = map(lambda x: int(x.split()[1],16),m)
#         push_per_block[bl]=numbers
#     return push_per_block

def preprocess_push(block,a,blocks_input):    
    b_source = blocks_input[block]
    comes_from = b_source.get_comes_from()
    for bl in comes_from:
        b = blocks_input[bl]
        contains = check_push_block(b,a)
        if contains:
            return block
        else:
            return preprocess_push(bl,a,blocks_input)
    return block

def check_push_block(block,a):
    instructions = block.get_instructions()
    m = filter(lambda x: x.split()[0][:-1]=="PUSH",instructions)
    numbers = map(lambda x: int(x.split()[1],16),m)
    if a in numbers :
        return True
    else:
        return False

def compute_push_blocks(pre_block,address,blocks_input):
    b_source = blocks_input[pre_block]
    comes_from = b_source.get_comes_from()
    push_blocks = {}
    if len(comes_from)!=len(address):
        print ("Error while looking for push blocks")
    else:
        for b in comes_from:
            block = blocks_input[b]
            instructions = block.get_instructions()
            m = filter(lambda x: x.split()[0][:-1]=="PUSH",instructions)
            numbers = map(lambda x: int(x.split()[1],16),m)
            push_address = filter(lambda x: x in numbers,address)
            if push_address != []:
                push_blocks[b]=numbers
            else:
                print("ERROR")
    return push_blocks
    
def get_push_block(m_blocks,address):
    block = -1
    for l in m_blocks:
        if address in m_blocks[l]:
            block = l
    return block

def get_common_predecessors(block,blocks_input):
    return get_common_predecessor_aux(block,blocks_input,[block.get_start_address()])

def get_common_predecessor_aux(block,blocks_input,pred):
    c = block.get_comes_from()
    # print "BLOCK"
    # print block.get_start_address()
    # print "COMES_FROM"
    # print c
    
    if len(c)>1:
        blocks = filter(lambda x: block.get_start_address() not in blocks_input[x].get_comes_from(),c)
        if len(blocks)>1:
            b = block.get_start_address()
            if b not in pred:
                pred.append(b)
        else:
            pred.append(blocks[0])
            get_common_predecessor_aux(blocks_input[blocks[0]],blocks_input,pred)
    else:
        pred.append(c[0])
        get_common_predecessor_aux(blocks_input[c[0]],blocks_input,pred)
    return pred

def get_stack_evol(block,inpt):
    i = inpt
    instr = block.get_instructions()
    for ins in instr:
        op = ins.split()
        op_info = opcodes.get_opcode(op[0])
        i = i-op_info[1]+op_info[2]
    return i

def check_loop(start_address_old,pred,blocks_input,jumps_to,falls_to,stack_in,idx,to_delete):
    global cloned_blocks

    new_child = -1
    if jumps_to not in pred: #it is the block to check
        child = blocks_input[jumps_to]
        stack_out = get_stack_evol(child,stack_in)
        if child.get_block_type() != "terminal":
            if start_address_old == child.get_jump_target():
                new_child = child.copy()
                new_child.set_jump_target(str(child.get_jump_target())+"_"+str(idx),True)
                stack_index[new_child.get_start_address()] = [stack_in,stack_out]
            elif start_address_old == child.get_falls_to():
                new_child = child.copy()
                new_child.set_falls_to(str(child.get_jump_target())+"_"+str(idx))
                stack_index[new_child.get_start_address()] = [stack_in,stack_out]
        else:
            comes_from = child.get_comes_from()
            if start_address_old in comes_from:
                i = comes_from.index(start_address_old)
                comes_from.pop(i)
            comes_from.append(str(start_address_old)+"_"+str(idx))
            child.set_comes_from(comes_from)

    elif falls_to not in pred:
        child = blocks_input[falls_to]
        stack_out = get_stack_evol(child,stack_in)
        if child.get_block_type() != "terminal":
            if start_address_old == child.get_jump_target():
                new_child = child.copy()
                new_child.set_start_address(str(new_child.get_start_address())+"_"+str(idx))
                new_child.set_jump_target(str(child.get_jump_target())+"_"+str(idx),True)
                new_child.update_list_jump_cloned(str(child.get_jump_target())+"_"+str(idx))
                stack_index[new_child.get_start_address()] = [stack_in,stack_out]
                
            elif start_address_old == child.get_falls_to():
                new_child = child.copy()
                new_child.set_start_address(str(new_child.get_start_address())+"_"+str(idx))
                new_child.set_falls_to(str(child.get_jump_target())+"_"+str(idx))
                stack_index[new_child.get_start_address()] = [stack_in,stack_out]
        else:
            comes_from = child.get_comes_from()
            if start_address_old in comes_from:
                i = comes_from.index(start_address_old)
                comes_from.pop(i)
            comes_from.append(str(start_address_old)+"_"+str(idx))
            child.set_comes_from(comes_from)
                
    if new_child != -1:
        # print "AQUI ESTA EL ERROR"
        # print start_address_old
        # print new_child.get_start_address()
        new_child = update_comes_from(new_child,start_address_old,idx)
        cloned_blocks.append(child.get_start_address())

        if child.get_start_address() not in to_delete:
                to_delete.append(child.get_start_address())
                
    return new_child

# def update_comes_from(block,pre_block,idx):
#     comes_from = block.get_comes_from()
#     if (pre_block in cloned_blocks) and (pre_block in comes_from):
#         i = comes_from.index(pre_block)
#         comes_from[i] = str(pre_block)+"_"+str(idx)
#         block.set_comes_from(comes_from)
#     return block

def get_split_start_address(address):
    a = str(address)
    idx = a.find("_")
    if idx == -1:
        return address
    else:
        it = 0
        while (idx != -1):
            prev_idx = idx
            idx = a.find("_",prev_idx+1)
            it = it+1
        if it == 1:
            return int(address[:prev_idx])
        else:
            return address[:prev_idx]

def update_block_cloned(new_block,pre_block,pred,idx,stack_in,blocks_input,to_delete):
    global cloned_blocks
    global stack_index

    stack_out = get_stack_evol(new_block,stack_in)

    new_block.set_stack_info((stack_in,stack_out))

    start_address_old = new_block.get_start_address()
    cloned_blocks.append(new_block.get_start_address())
    new_block.set_start_address(str(start_address_old)+"_"+str(idx))
    
    jumps_to = new_block.get_jump_target()
    falls_to = new_block.get_falls_to()

    new_block = update_comes_from(new_block,pre_block,idx)
    
    #check loop
    if new_block.get_block_type() == "conditional":
        r = check_loop(start_address_old,pred,blocks_input,jumps_to,falls_to,stack_in,idx,to_delete)
        if r != -1:
            # r.display()
            blocks_input[r.get_start_address()] = r
            r_start_address = get_split_start_address(r.get_start_address())
            update_comes_from(new_block,r_start_address,idx)
    else:
        r = -1
        
    if jumps_to in pred:
        new_block.set_jump_target(str(jumps_to)+"_"+str(idx),True)
        new_block.update_list_jump_cloned(str(jumps_to)+"_"+str(idx))
        if r !=-1:
            new_block.set_falls_to(r.get_start_address())
    else:
        new_block.set_falls_to(str(falls_to)+"_"+str(idx))
        if r != -1:
            new_block.set_jump_target(r.get_start_address(),True)
            new_block.update_list_jump_cloned(r.get_start_address())

    stack_index[new_block.get_start_address()] = [stack_in,stack_out]

    # print "TODELETE INSIDE"
    # print to_delete
    return new_block, blocks_input

def delete_old_blocks(blocks_to_remove, blocks):
    for block in blocks_to_remove:
        del blocks[block]

        
def modify_jump_first_block(block_obj,source_block,idx):
    if block_obj.get_falls_to() == source_block:
        block_obj.set_falls_to(str(source_block)+"_"+str(idx))
        #blocks_input[push_block] = push_block_obj
        block_obj.update_list_jump_cloned(str(source_block)+"_"+str(idx))

    else:
        block_obj.set_jump_target(str(source_block)+"_"+str(idx),True)
        #blocks_input[push_block] = push_block_obj
        block_obj.update_list_jump_cloned(str(source_block)+"_"+str(idx))

def modify_last_block(block,stack_in,idx,pred,pre_block,address):
    global cloned_blocks
    global stack_index
    
    stack_out = get_stack_evol(block,stack_in)
    block.set_stack_info((stack_in,stack_out))

    cloned_blocks.append(block.get_start_address())
    block.set_start_address(str(block.get_start_address())+"_"+str(idx))

    stack_index[block.get_start_address()] = [stack_in,stack_out]
    
    if (len(pred) != 1):
        comes_from = block.get_comes_from()
            
        if (pre_block in cloned_blocks) and (pre_block in comes_from):
            pos = comes_from.index(pre_block)
            comes_from[pos] = str(pre_block)+"_"+str(idx)
            block.set_comes_from(comes_from)
    else: #It is the only block
        block.set_comes_from([pre_block])
            
    block.set_jump_target(address,True) #By definition
    block.set_list_jump(filter(lambda x: x == address,block.get_list_jumps()))
    return block

def modify_target_block(target_block,block_cloned,last_block):
    comes_from = target_block.get_comes_from()
    if (block_cloned.get_start_address() in comes_from):
        idx = comes_from.index(block_cloned.get_start_address())
        comes_from[idx] = last_block.get_start_address()
        target_block.set_comes_from(comes_from)

def clone(block, blocks_input):
    global cloned_blocks
    global stack_index

    blocks_dict = blocks_input
    uncond_block = block.get_start_address()
    #pred = get_common_predecessors(block, blocks_dict)
    #to_delete = pred[:]
    
    address = block.get_list_jumps()
    n_clones = len(address)
    
    #source_path = pred[-1]

    b = preprocess_push(uncond_block,address[0],blocks_dict)
    
    in_blocks = compute_push_blocks(b,address,blocks_dict)
    #cloned_blocks = cloned_blocks+pred
    
    to_delete = []
    cloned = []
    i = 0
    
    while (i<n_clones): #bucle que hace las copias

        #clonar
        a = address[i]
        # print "ESTO ES LO QUE CALCULA"
        # print a
        # print in_blocks
        push_block = get_push_block(in_blocks,a)

        stack_in = stack_index[push_block][1]
        #print "EMPIEZA"

        #cambio el primero
        push_block_obj = blocks_dict[push_block]
        modify_jump_first_block(push_block_obj,b,i)
        
        #clonamos todo el camino hasta el destino
        cloned = []
        clone_block(b,push_block,block.get_start_address(),blocks_dict,i,stack_in,to_delete,cloned,-1)

        clone_last_block(uncond_block, a, push_block, blocks_dict,i,cloned)

        address_block = blocks_dict[a]
        comes_from = address_block.get_comes_from()
        idx = comes_from.index(uncond_block)
        comes_from[idx] = str(comes_from[idx])+"_"+str(i)
        
        if uncond_block not in to_delete:
            to_delete.append(uncond_block)

        #print "ITERACION "+str(i)
           # print e.get_comes_from()
        #print push_block
        
        # #modified the jump address of the first block
        # # print "PUSHBLOCK ERROR"
        # # print push_block
        
        # push_block_obj = blocks_dict[push_block]
        # modify_jump_first_block(push_block_obj,source_path,i)
        
        # #we copy the last block
        # pre_block = push_block
        # # print "PUSH"
        # # print pre_block
        # # print "ADDRESS"
        # # print a
        # first = True
        # stack_in = stack_index[pre_block][1]

        # #We start to clone each path
        # for idx in xrange(len(pred)-1,0,-1):
        #     new_block = blocks_dict[pred[idx]].copy()
        #     # print "TYPE"
        #     # print new_block.get_block_type()
        #     # new_block = copy.deepcopy(blocks_input[pred[idx]])
        #     new_block, blocks_dict  = update_block_cloned(new_block,pre_block,pred,i,stack_in,blocks_dict,to_delete)
            
        #     # print "CLONED"
        #     # new_block.display()
        #     # print new_block.get_comes_from()
        #     if first == True:
        #         first = False
        #         comes_from = [push_block]
        #         new_block.set_comes_from(comes_from)
                
        #     blocks_dict[new_block.get_start_address()] = new_block
        #     pre_block = pred[idx]
        #     stack_in = new_block.get_stack_info()[1]
            

        # if first: #It means that the block to copy has no predecessor
        #     stack_in = stack_index[pre_block][1]
        # else:
        #     stack_in = new_block.get_stack_info()[1]
            
        # #We modify the last block
        # new_block = blocks_dict[pred[0]].copy()
        # # new_block = copy.deepcopy(blocks_input[pred[0]])
        # new_block = modify_last_block(new_block,stack_in,i,pred,pre_block,a)
        # blocks_dict[new_block.get_start_address()] = new_block
        
        # #Target block
        # target_block = blocks_dict[a]
        # modify_target_block(target_block,block,new_block)
        
        i = i+1
    # print "TO DELETE"
    # print to_delete
    # for e in blocks_dict.values():
    #     e.display() 
    delete_old_blocks(to_delete,blocks_dict)
    #for e in blocks_input.values():
    #     e.display()
    #     print e.get_comes_from()

    #return blocks_dict

def  clone_block(block_address, push_block, end_address, blocks_input, idx, stack_in, to_delete,cloned,pred):
    global stack_index

    if block_address != end_address and block_address not in cloned:
        
        block = blocks_input[block_address]
        comes_from_old = block.get_comes_from()
        
        block_dup = block.copy()
        stack_out = get_stack_evol(block_dup,stack_in)
        block_dup.set_stack_info((stack_in,stack_out))

        start_address_old = block.get_start_address()
        block_dup.set_start_address(str(start_address_old)+"_"+str(idx))
        stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
        
        jumps_to = block_dup.get_jump_target()
        falls_to = block_dup.get_falls_to()
        cloned.append(block_address)

        if pred !=-1:
            block_dup.add_origin(pred)
        else:
            pred_end = filter(lambda x: x == push_block,comes_from_old)
            block_dup.set_comes_from(pred_end)
            
        blocks_input[block_dup.get_start_address()]=block_dup
        clone_child(block_dup,jumps_to,falls_to,idx,push_block,end_address,blocks_input,stack_out,to_delete,cloned,pred)

      #  block_dup.display()
       # block_dup.display()
        if block_address not in to_delete:
            to_delete.append(block_address)

def clone_child(block_dup,jumps_to,falls_to,idx,push_block,end_address,blocks_input,stack_out,to_delete,cloned,pred):
    t =  block_dup.get_block_type()
    pred_new = block_dup.get_start_address()
    if t == "conditional":
        block_dup.set_jump_target(str(jumps_to)+"_"+str(idx),True)
        block_dup.update_list_jump_cloned(str(jumps_to)+"_"+str(idx))
        if jumps_to not in cloned:
            clone_block(jumps_to, push_block, end_address,blocks_input,idx,stack_out,to_delete,cloned,pred_new)
        else:
            blocks_input[str(jumps_to)+"_"+str(idx)].add_origin(pred_new)

        block_dup.set_falls_to(str(falls_to)+"_"+str(idx))
        if  falls_to not in cloned:
            clone_block(falls_to,push_block, end_address,blocks_input,idx,stack_out,to_delete,cloned,pred_new)
        else:
            blocks_input[str(falls_to)+"_"+str(idx)].add_origin(pred_new)
            
    elif t == "unconditional":
        block_dup.set_jump_target(str(jumps_to)+"_"+str(idx),True)
        block_dup.update_list_jump_cloned(str(jumps_to)+"_"+str(idx))
        if  jumps_to not in cloned:
            clone_block(jumps_to, push_block, end_address,blocks_input,idx,stack_out,to_delete,cloned,pred_new)
        else:
            blocks_input[str(jumps_to)+"_"+str(idx)].add_origin(pred_new)
    elif t == "falls_to":
        block_dup.set_falls_to(str(falls_to)+"_"+str(idx))
        if  falls_to not in cloned:
            clone_block(falls_to,push_block, end_address,blocks_input,idx,stack_out,to_delete,cloned,pred_new)
        else:
            blocks_input[str(falls_to)+"_"+str(idx)].add_origin(pred_new)

def clone_last_block(block_address, a, push_block, blocks_input,idx,cloned):
    global stack_index

    block = blocks_input[block_address]
    block_dup = block.copy()
    comes_from = block.get_comes_from()
    pred_old = comes_from[0]
    if pred_old in cloned:
        pred = str(pred_old)+"_"+str(idx)
    else:
        pred = pred_old

    
    stack_in = stack_index[pred][1]
    stack_out = get_stack_evol(block_dup,stack_in)

    block_dup.set_stack_info((stack_in,stack_out))

    block_dup.set_start_address(str(block.get_start_address())+"_"+str(idx))
    stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
            
    block_dup.set_jump_target(a,True) #By definition
    block_dup.set_list_jump(filter(lambda x: x == a,block.get_list_jumps()))
    new_comes_from = update_comes_from(comes_from,idx,push_block,cloned)
    block_dup.set_comes_from(new_comes_from)
    blocks_input[block_dup.get_start_address()]=block_dup


def update_comes_from(pred_list,idx,address,cloned):
    comes_from = []

    for b in pred_list:
        if b in cloned:
            comes_from.append(str(b)+"_"+str(idx))
        else:
            comes_from = filter(lambda x: x == address,pred_list)
    return comes_from
def compute_cloning(blocks_to_clone,blocks_input,stack_info):
    global stack_index
    
    init()
    blocks_dict = blocks_input
    stack_index = stack_info
    
    blocks2clone = sorted(blocks_to_clone, key = getLevel)
    for b in blocks2clone:
        clone(b,blocks_dict)

    # print "AQUI"
    # blocks_dict['4416_1'].display()
    # for e in blocks_dict.values():
    #     e.display()
    #return stack_index

    
