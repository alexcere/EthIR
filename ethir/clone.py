import opcodes
from utils import getLevel, getKey
import os
from dot_tree import Tree, build_tree

def init():
    global cloned_blocks
    cloned_blocks = []

    global stack_index
    stack_index = {}

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

'''
Given the list of blocks, the final address of the path, the address of the block that pushes that final address
and the block which needs to be copied, copies the whole path that goes across that block. Includes a flag indicating
whether this is first time last block is being copied. This is used in case there're several paths that end in the same final
address.
'''
def clone_path(blocks_dict, final_address, push_address, block, idx, first_copy, globally_cloned):
    global cloned_blocks
    global stack_index

    stack_in = stack_index[push_address][1]
    #print "EMPIEZA"

    #Empezamos a clonar desde los hijos del bloque que ha hecho el push
    #No se clona el bloque que ha hecho el push, asi que llamamos directamente
    #a clone_child.
        
    push_block_obj = blocks_dict[push_address]

    final_block_obj = blocks_dict[final_address]

    locally_cloned = []

    # Preguntamos el camino en el bloque que queremos la direccion final.
    # Si lo preguntasemos en block, podriamos quedarnos con caminos mas largos de los que
    # nos interesan, pues puede ser un bucle y pasar varias veces por ese camino.
    
    path_to_clone = get_main_path(final_block_obj.get_paths(), push_address)
    print("Clonando")
    # print push_address
    print path_to_clone
    #modify_jump_first_block(push_block_obj,b,i)

    initial_jumps_to = push_block_obj.get_jump_target()

    # print initial_jumps_to

    initial_falls_to = push_block_obj.get_falls_to()

    #No vamos a separar el ultimo bloque del resto. Cuando lleguemos al final del todo,  
    clone_child(push_block_obj,initial_jumps_to, initial_falls_to,idx,push_address,block.get_start_address(),blocks_dict,stack_in,globally_cloned,locally_cloned, path_to_clone,1)

    if len(path_to_clone) == 3:
        pred = path_to_clone[-3]
    else:
        pred = locally_cloned[-1] + "_" + str(idx)
    
    if first_copy:
        #Anyadimos el ultimo bloque a clonar, si no se ha hecho antes.
        start_address = block.get_start_address()
        if start_address not in globally_cloned:
            globally_cloned.append(block.get_start_address())
        #Clonamos el ultimo bloque teniendo en cuenta que la direccion de salto puede ser una copia.
        #Su predecesor es el ultimo bloque que hemos clonado.
        clone_last_block(start_address, final_address, blocks_dict,idx,locally_cloned, pred, push_address)
    else:
        block[str(block.get_start_address()) + '_' + idx].add_origin(pred)
    

'''
Given a list of paths from the initial node to the node, and a
block address; finds a subpath that starts in that address. Error if 
not found a path with that address.
'''
def get_main_path(paths, address):
    for path in paths:
        if address in path:
            return path[path.index(address):]#TODO: Find start point and return it
    raise Exception('Path containing address not found')
    
    
def clone(block, blocks_input, address_dict, globally_cloned):
    global cloned_blocks
    global stack_index

    blocks_dict = blocks_input
    uncond_block = block.get_start_address()    
    address = block.get_list_jumps()
 
    n_clones = len(address)
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

        #Cogemos el bloque que ha hecho push a la direccion
        push_addresses = address_dict[a]

        first_copy = True

        # print("Direcciones de push")
        # print push_addresses
        
        #Copiamos cada camino que haga un push al bloque final que estamos considerando
        for push_address in push_addresses:
            #Si ya hemos clonado el nodo que ha hecho el push, entonces el camino que estamos
            #considerando es un subcamino de uno mas largo que ya hemos clonado.
            if push_address not in globally_cloned:
                clone_path(blocks_dict, a, push_address, block, i, first_copy, globally_cloned)
                first_copy = False

        i = i+1
        
    # El borrado se lleva a cabo una vez hemos hecho todo el cloning.


def  clone_block(block_address, push_block, end_address, blocks_input, idx, stack_in, globally_cloned,locally_cloned,pred, path_to_clone, path_idx):
    global stack_index

    if block_address != end_address and block_address not in locally_cloned:
        
        block = blocks_input[block_address]
        comes_from_old = block.get_comes_from()
        #TODO: quizas actualizar el comes from del bloque que no se va a borrar.
        
        block_dup = block.copy()
        stack_out = get_stack_evol(block_dup,stack_in)
        block_dup.set_stack_info((stack_in,stack_out))

        start_address_old = block.get_start_address()
        block_dup.set_start_address(str(start_address_old)+"_"+str(idx))
        stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
        
        jumps_to = block_dup.get_jump_target()
        falls_to = block_dup.get_falls_to()
        locally_cloned.append(block_address)
        
        #Solo se pone el origen del que viene, pues se empieza directamente desde el clone_child
        block_dup.add_origin(pred)

        print("Copiando bloque")
        print(str(start_address_old) + "_" + str(idx))

        # #Nos quedamos con los caminos que han pasado por el push.
        # paths_in = filter(lambda x: push_block in x, block.get_paths())
        # block_dup.set_paths(paths_in)

        # #Del nodo original, quitamos los caminos que hacen ese push.
        # paths_not_in = filter(lambda x: push_block not in x, block.get_paths())
        # block.set_paths(paths_not_in)
        
        blocks_input[block_dup.get_start_address()]=block_dup
        clone_child(block_dup,jumps_to,falls_to,idx,push_block,end_address,blocks_input,stack_out,globally_cloned,locally_cloned, path_to_clone, path_idx)

        #block_dup.display()
       # block_dup.display()
        if block_address not in globally_cloned:
            globally_cloned.append(block_address)

            
def update_jump_target(block_dup, jumps_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):
   block_dup.set_jump_target(str(jumps_to)+"_"+str(idx),True)
   
   block_dup.set_list_jump([str(jumps_to)+"_"+str(idx)])
   if jumps_to not in locally_cloned:
       
       # print block_dup.get_list_jumps()
       
       clone_block(jumps_to, push_block, end_address,blocks_input,idx,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)
   else:
       blocks_input[str(jumps_to)+"_"+str(idx)].add_origin(pred_new)
       

def update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):
    block_dup.set_falls_to(str(falls_to)+"_"+str(idx))
    if  falls_to not in locally_cloned:
        clone_block(falls_to,push_block, end_address,blocks_input,idx,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)
    else:
        blocks_input[str(falls_to)+"_"+str(idx)].add_origin(pred_new)

def clone_child(block_dup,jumps_to,falls_to,idx,push_block,end_address,blocks_input,stack_out,globally_cloned,locally_cloned,path_to_clone, path_idx):
    t =  block_dup.get_block_type()
    pred_new = block_dup.get_start_address()
    if t == "conditional":
        if path_idx == -1:
            update_jump_target(block_dup, jumps_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)

        else:
            if path_to_clone[path_idx] == jumps_to:
                update_jump_target(block_dup, jumps_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            elif path_to_clone[path_idx] == falls_to:
                update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_jump_target(block_dup, jumps_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            else:
                raise Exception("Not consistent path")
            
    #Como los caminos no se actualizan, solo utilizamos el path_to_clone si el bloque incondicional
    #no ha sido clonado aun. En caso de haber sido clonado, ya hemos considerado un solo camino, y
    #por tanto nos podemos quedar directamente con quien hace el salto condicional.
    elif t == "unconditional":
        
        if path_idx != -1:

            # Se comprueba la condicion de solo tener un salto disponible (ya sea porque solo tenia
            # uno desde el principio, o se ha clonado y se ha quedado con uno)
            print("Con jump:")
            print jumps_to
            print block_dup.get_list_jumps()
            
            if len(block_dup.get_list_jumps()) == 1:
                # print("He llegado con ")
                # print pred_new
                update_jump_target(block_dup, jumps_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
            else:
                print("Cojo el camino del path")
                update_jump_target(block_dup, path_to_clone[path_idx], idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
        else:
            #TODO: clonar todos los bloques que salen a partir de aqui por caminos separados
            print("Salto incondicional fuera del camino principal")
        
    elif t == "falls_to":
        if path_idx == -1:
            update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
        else:
            update_falls_to(block_dup, falls_to, idx, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx + 1)


            
def clone_last_block(block_address, a, blocks_input,idx,locally_cloned, pred, push_address):
    global stack_index
    
    block = blocks_input[block_address]
    block_dup = block.copy()
    comes_from = block.get_comes_from()

    stack_in = stack_index[pred][1]
    stack_out = get_stack_evol(block_dup,stack_in)

    block_dup.set_stack_info((stack_in,stack_out))

    print("Copiando ultimo bloque:")
    print(str(block.get_start_address())+"_"+str(idx))

    block_dup.set_start_address(str(block.get_start_address())+"_"+str(idx))
    stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
            
    block_dup.set_jump_target(a,True) #By definition
    block_dup.set_list_jump([a])
    #new_comes_from = update_comes_from(comes_from,idx,push_block,cloned)
    block_dup.add_origin(pred)

    #Nos quedamos con los caminos que han pasado por el push.
    paths_in = filter(lambda x: push_address  in x, block.get_paths())
    block_dup.set_paths(paths_in)

    #Del nodo original, quitamos los caminos que hacen ese push.
    paths_not_in = filter(lambda x: push_address not in x, block.get_paths())
    block.set_paths(paths_not_in)
    
    blocks_input[block_dup.get_start_address()]=block_dup

    blocks_input[a].update_comes_from(str(block.get_start_address())+"_"+str(idx))
    

def update_comes_from(pred_list,idx,address,cloned):
    comes_from = []

    for b in pred_list:
        if b in cloned:
            comes_from.append(str(b)+"_"+str(idx))
        else:
            comes_from = filter(lambda x: x == address,pred_list)
    return comes_from


def get_minimum_len(paths):
    l = map(lambda x: len(x),paths)
    return min(l)                

'''
blocks_to_clone-> lista con los bloques a clonar
blocks_input: diccionario clave valor-> clave: address del bloque; valor: el bloque
stack_info: diccionario clave: address del bloque; valor: lista con el tamanyo de la stack a la entrada y a la salida
address_dict: diccionario clave: push en la pila; valor: bloque que ha hecho ese push 
'''
def compute_cloning(blocks_to_clone,blocks_input,stack_info, address_dict):
    global stack_index
    
    init()
    blocks_dict = blocks_input
    stack_index = stack_info
    
    blockps2clone = sorted(blocks_to_clone, key = getLevel)
    globally_cloned = []

    for b in blockps2clone:
        clone(b, blocks_dict, address_dict, globally_cloned)

    print globally_cloned
    delete_old_blocks(globally_cloned, blocks_input)

    # print ("Copias")
    # print blocks_input['361_1'].get_list_jumps()
    # print blocks_input['361_1'].get_jump_target()
    # print blocks_input['361_1'].get_falls_to()
    show_graph(blocks_input)



def show_graph(blocks_input):
    for address in blocks_input:
        print("Bloque: ")
        print address
        print blocks_input[address].get_comes_from()
        print blocks_input[address].get_list_jumps()
