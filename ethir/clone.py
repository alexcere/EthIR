import opcodes
from utils import getLevel, getKey
import os
from dot_tree import Tree, build_tree

def init():
    global cloned_blocks
    cloned_blocks = []

    global stack_index
    stack_index = {}

### TODO: Ahora no 'busco' quien me hace el push,
### tengo algún tipo de diccionario que me lo busca.
def preprocess_push(block,addresses,blocks_input):    
    #print addresses
    b_source = blocks_input[block]
    comes_from = b_source.get_comes_from()
    # print "INI"
    # print block
    # print comes_from
    
    for bl in comes_from:
        b = blocks_input[bl]
        contains = check_push_block(b,addresses)
        if contains:
            return block
        
    block = preprocess_push(comes_from[0],addresses,blocks_input)
    return block

def get_relation_stack_address(addrs,stacks):
    i = 0
    for e in addrs:
        l = filter(lambda x: e in x,stacks)
        if len(l) >0:
            i = i+1
    return i == len(addrs)

def preprocess_push2(block,addresses,blocks_input):
    b_source = blocks_input[block]
    comes_from = b_source.get_comes_from()

    valid = True
    for bl in comes_from:
        b = blocks_input[bl]
        stacks = b.get_stacks()
        valid = valid and get_relation_stack_address(addresses,stacks)

    if not valid:
        return block
    else:
        return preprocess_push2(comes_from[0],addresses,blocks_input)
    
def check_push_block(block,addresses):
    instructions = block.get_instructions()
    m = filter(lambda x: x.split()[0][:-1]=="PUSH",instructions)
    numbers = map(lambda x: int(x.split()[1],16),m)
    end_list = filter(lambda x: x in numbers,addresses)
    # if a in numbers :
    if len(end_list)>0:
        return True
    else:
        return False

'''
Is correct if the number of stacks that contain each block
(address) to clone is the same as the different address to clone. We
get one different stack per clonning at b. (The one that spawns the
different paths).

'''    
def is_correct_preprocess_push(b,addresses,blocks_input):
    stacks = blocks_input[b].get_stacks()
    num = 0
    for e in addresses:
        r = filter(lambda x: e in x,stacks)
        if len(r) > 0:
            num = num + 1

    return (num == len(addresses))


def get_address_from_stacks(addresses,stacks):
    r = []
    for s in stacks:
        new = filter(lambda x: x in s,addresses)
        if new not in r:
            r.append(new)
    if len(r) == 1:
        return r[0][0]
    else:
        print ("Error in compute_push_blocks")
def compute_push_blocks(pre_block,address,blocks_input):
    b_source = blocks_input[pre_block]
    comes_from = b_source.get_comes_from()
    push_blocks = {}
    # print "PREPRE"
    # print pre_block
    # print "STACKS"
    # print comes_from
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
                stacks = block.get_stacks()
                a = get_address_from_stacks(address,stacks)
                
                push_blocks[b] = [a]

    return push_blocks


#NOTE: No va a hacer falta
def search_push_blocks(pre_block,address,blocks_input):
    b_source = blocks_input[pre_block]
    comes_from = b_source.get_comes_from()
    #print comes_from
    for b in comes_from:
        block = blocks_input[b]
        instructions = block.get_instructions()
        m = filter(lambda x: x.split()[0][:-1]=="PUSH",instructions)
        numbers = map(lambda x: int(x.split()[1],16),m)
        push_address = filter(lambda x: x in numbers,address)
        if push_address != []:
            return numbers

        else:
            return search_push_blocks(b,address,blocks_input)

#NOTE: No va a hacer falta
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

#NOTE: Este va a hacer falta
def get_stack_evol(block,inpt):
    i = inpt
    instr = block.get_instructions()
    for ins in instr:
        op = ins.split()
        op_info = opcodes.get_opcode(op[0])
        i = i-op_info[1]+op_info[2]
    return i


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

def clean_address(l,in_blocks,current):
        concat = []
        for b in in_blocks:
            if b != current:
                concat = concat+in_blocks[b]

        for a in concat:
            # print "IS A: "+str(a)
            if a in l:
                l.remove(a)
        return l

def clean_in_blocks(in_blocks,address):
    for a in in_blocks:
        e = in_blocks[a]
        if len(e)>1:
            l = filter(lambda x: x in address,e)
            # print l
            l = clean_address(l,in_blocks,a)
            in_blocks[a] = l
            
def clone(block, blocks_input):
    global cloned_blocks
    global stack_index

    blocks_dict = blocks_input
    uncond_block = block.get_start_address()    
    address = block.get_list_jumps()
 
    n_clones = len(address)
    
    #source_path = pred[-1]

    b = preprocess_push(uncond_block,address,blocks_dict)
    v = is_correct_preprocess_push(b,address,blocks_dict)

    # print "PRE"
    # print b
    # print blocks_dict[b].get_stacks()
    # print address
    # print v
    
    if not v:
        b = preprocess_push2(uncond_block,address,blocks_dict)
    # print b
        
    in_blocks = compute_push_blocks(b,address,blocks_dict)
    # print "EMPIEZA LA LIMPIEZA"
    clean_in_blocks(in_blocks,address)
    # print in_blocks
    #cloned_blocks = cloned_blocks+pred
    #print in_blocks
    to_delete = []
    cloned = []
    i = 0
    
    while (i<n_clones): #bucle que hace las copias

        #clonar
        a = address[i]
        # print "ESTO ES LO QUE CALCULA"
        # print a
        # print in_blocks
        # print "CLONANDO"
        # print uncond_block
        # print b
        push_block = get_push_block(in_blocks,a)

        # print push_block
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
        
        i = i+1

    delete_old_blocks(to_delete,blocks_dict)


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
        #? Que es pred
        if pred !=-1:
            block_dup.add_origin(pred)
        else:
            pred_end = filter(lambda x: x == push_block,comes_from_old)
            block_dup.set_comes_from(pred_end)
            
        blocks_input[block_dup.get_start_address()]=block_dup
        clone_child(block_dup,jumps_to,falls_to,idx,push_block,end_address,blocks_input,stack_out,to_delete,cloned,pred)

        #block_dup.display()
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

    if push_block in comes_from:
        pred_old = push_block

    else:
        pred_old = comes_from[0]
    
    # pred_old = comes_from[0]
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

###NOTE: De aqui hacia abajo busca el orden. No hace falta
def get_continue_cloning(cloned,blocks):
    addresses = map(lambda x: x.get_start_address(),blocks)
    all_cloned_list = filter(lambda x: x not in cloned,addresses)
    return not(len(all_cloned_list)==0)

def get_minimum_len(paths):
    l = map(lambda x: len(x),paths)
    return min(l)

def choose_block_to_clone(blocks2clone, components,blocks,cloned):
    l = len(blocks2clone)
    i = 0
    found = False
    next_clone = -1
    # print "START"
    
    '''
    Clono el nodo si:
    - ninguno de los nodos a clonar esta en mi componente (los nodos desde los que llego a mi)
    - si lo esta, ya ha sido clonado.
    '''
    incidencia = []
    while(i<l and not found):
        b = blocks2clone[i]
        addr = b.get_start_address()
        if addr not in cloned:
            my_component = components[addr]
            blocks_dep = filter(lambda x: x.get_start_address() in my_component and x.get_start_address()!=addr, blocks2clone)
            aa = map(lambda x: x.get_start_address(),blocks_dep)
            # print "ADDR "+str(addr)
#            print aa
            if len(blocks_dep)==0:
                next_clone = b
                found = True

            else:
                incidencia.append((len(blocks_dep),addr))
                already_cloned = filter(lambda x: x.get_start_address() not in cloned,blocks_dep)
                if len(already_cloned)==0:
                    next_clone = b
                    found = True
        i = i+1

    '''
    Si al salir del bucle no tengo candidato es porque tengo un ciclo.
    Cojo el que menos componentes tenga. (En teoria mas arriba esta).
    Si hay varios iguales (deberia) cojo el de menor depth.
    '''
    
    if next_clone == -1:
        mini = float('inf')
        for ind,_ in incidencia:
            if ind < mini:
                mini = ind

        bs_aux = filter(lambda x: x[0] == mini, incidencia)
        bs = map(lambda x: x[1],bs_aux)
        
        if len(bs)==1:
            # print "UNO UNO"
            next_clone = blocks[bs[0]]

        
        # Si tengo varios con menor incidencia, computo cual esta delante en el ciclo gracias a los caminos.
        # Cojo los caminos y filtro los elementos con incidencia minima. Aque con camino minimo me lo quedo.
        
        
        else:
            mini = float('inf')
            b = ""
            for a in bs:
                # print "A: "+str(a)
                # print blocks[a].get_depth_level()
                p =  map(lambda x: filter(lambda y: y in bs and y not in cloned,x),blocks[a].get_paths())
                # print p
                #l = len(p[0])
                l = get_minimum_len(p)
                if l<mini:
                    mini = l
                    b = a
                    # print "B: "+str(b)
                # b =  map(lambda x: filter(lambda y: y in bs_aux,x),blocks[bs[1][1]].get_paths())
            # bs_d = map(lambda x: (blocks[x].get_depth_level(),x),bs)
            # end = sorted(bs_d)
            
            next_clone = blocks[b]

    return next_clone
                

'''
blocks_to_clone-> lista con los bloques a clonar
blocks_input: diccionario clave valor-> clave: address del bloque; valor: el bloque
stack_info: diccionario clave: address del bloque; valor: lista con el tamaño de la stack a la entrada y a la salida
component_of: diccionario clave: address; valor: lista de los nodos que llegan al bloque address
addres_dict: diccionario clave: valor de algún push en la pila (contiene todos los push 
'''
def compute_cloning(blocks_to_clone,blocks_input,stack_info,component_of):
    global stack_index
    
    init()
    blocks_dict = blocks_input
    stack_index = stack_info
    
    blockps2clone = sorted(blocks_to_clone, key = getLevel)
    cloned = []

    continue_cloning = True
    # for e in blocks_to_clone:
    #     print e.get_start_address()
    while(continue_cloning):
        # print blocks_input.keys()
        b = choose_block_to_clone(blocks2clone,component_of,blocks_input,cloned)
        # print "********************"
        # print b.get_start_address()
        clone(b,blocks_dict)
        cloned.append(b.get_start_address())
        continue_cloning = get_continue_cloning(cloned,blocks2clone)
        #print "CLONED: "+str(cloned)+"\n"
