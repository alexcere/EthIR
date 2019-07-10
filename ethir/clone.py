import opcodes
from utils import getLevel, get_initial_block_address, get_next_block_address
import os
from dot_tree import Tree, build_tree

def init():
    global cloned_blocks
    cloned_blocks = []

    global stack_index
    stack_index = {}

    global cloned_block_counter
    cloned_block_counter = {}

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
def clone_path(blocks_dict, final_address, push_address, block, first_copy, globally_cloned, index_dict):
    global cloned_blocks
    global stack_index
    global cloned_block_counter

    
    stack_in = stack_index[push_address][1]
    #print "EMPIEZA"

    #Empezamos a clonar desde los hijos del bloque que ha hecho el push
    #No se clona el bloque que ha hecho el push, asi que llamamos directamente
    #a clone_child.
        
    push_block_obj = blocks_dict[push_address]

    final_block_obj = blocks_dict[final_address]

    locally_cloned = []
    cloned_block_counter = {}
    
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
    clone_child(push_block_obj,initial_jumps_to, initial_falls_to,index_dict,push_address,block.get_start_address(),blocks_dict,stack_in,globally_cloned,locally_cloned, path_to_clone,1)

    pred = path_to_clone[-3]

    # Si el camino tiene mas de 3 direcciones, entonces el predecesor
    # del bloque a clonar tambien ha sido clonado, y por tanto, hay que
    # anyadir el indice correspondiente.
    
    if len(path_to_clone) > 3:
        pred = str(pred) + "_" +  str(index_dict[pred] - 1)

    start_address = block.get_start_address()
        
    if first_copy:
        #Anyadimos el ultimo bloque a clonar, si no se ha hecho antes.
        if start_address not in globally_cloned:
            globally_cloned.append(block.get_start_address())
        #Clonamos el ultimo bloque teniendo en cuenta que la direccion de salto puede ser una copia.
        #Su predecesor es el ultimo bloque que hemos clonado.
        clone_last_block(start_address, final_address, blocks_dict,index_dict,locally_cloned, pred, push_address)
    else:
        block[str(start_address) + '_' + str(index_dict[address_wth_idx] - 1)].add_origin(pred)
    

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
    
    
def clone(block, blocks_input, address_dict, globally_cloned, index_dict):
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
        print "ESTO ES LO QUE CALCULA"
        print a

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
                clone_path(blocks_dict, a, push_address, block, first_copy, globally_cloned, index_dict)
                first_copy = False
        i = i+1
        
    # El borrado se lleva a cabo una vez hemos hecho todo el cloning.


def  clone_block(block_address, push_block, end_address, blocks_input, idx_dict, stack_in, globally_cloned,locally_cloned,pred, path_to_clone, path_idx):
    global stack_index
    global cloned_block_counter

    
    # La comprobacion se hace a la hora de hacer el update correspondiente de si
    # ha sido clonado o no. Asi, permitimos que un mismo bloque se pueda clonar varias veces.
    if block_address != end_address:
    #if block_address != end_address and block_address not in locally_cloned:
        
        block = blocks_input[block_address]
        comes_from_old = block.get_comes_from()
        #TODO: quizas actualizar el comes from del bloque que no se va a borrar.
        
        block_dup = block.copy()
        stack_out = get_stack_evol(block_dup,stack_in)
        block_dup.set_stack_info((stack_in,stack_out))

        old_start_address = block.get_start_address()
        new_start_address = get_next_block_address(old_start_address, idx_dict)
        idx_dict[get_initial_block_address(old_start_address)] += 1
        
        block_dup.set_start_address(new_start_address)
        stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
        
        jumps_to = block_dup.get_jump_target()
        falls_to = block_dup.get_falls_to()
        locally_cloned.append(block_address)
        
        cont = cloned_block_counter.get(block_address,0)
        cloned_block_counter[block_address] = cont+1
        
        #Solo se pone el origen del que viene, pues se empieza directamente desde el clone_child
        block_dup.add_origin(pred)

        print("Copiando bloque")
        print(new_start_address)

        # #Nos quedamos con los caminos que han pasado por el push.
        # paths_in = filter(lambda x: push_block in x, block.get_paths())
        # block_dup.set_paths(paths_in)

        # #Del nodo original, quitamos los caminos que hacen ese push.
        # paths_not_in = filter(lambda x: push_block not in x, block.get_paths())
        # block.set_paths(paths_not_in)
        
        blocks_input[block_dup.get_start_address()]=block_dup
        clone_child(block_dup,jumps_to,falls_to,idx_dict,push_block,end_address,blocks_input,stack_out,globally_cloned,locally_cloned, path_to_clone, path_idx)

        #locally_cloned only keeps the current execution path that leads to clone things
        locally_cloned.pop()
        
        #block_dup.display()
       # block_dup.display()
        if block_address not in globally_cloned:
            globally_cloned.append(block_address)

            
def update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):

    # No clonamos si el bloque ya ha sido clonado y esta fuera del camino principal.
    if (jumps_to in locally_cloned) and (path_idx == -1):

        jump_address = find_sucessor_block(idx_dict, jumps_to)
        
        block_dup.set_jump_target(jump_address, True)
        block_dup.set_list_jump([jump_address])

        blocks_input[jump_address].add_origin(pred_new)

    else:
        new_jump_address = get_next_block_address(jumps_to, idx_dict)
        block_dup.set_jump_target(new_jump_address,True)
        block_dup.set_list_jump([new_jump_address])

       # print block_dup.get_list_jumps()
       
        clone_block(jumps_to, push_block, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)

def find_sucessor_block(idx_dict, next_address):
    prefix_address = get_initial_block_address(next_address)
    return str(prefix_address) + "_" + str(idx_dict[prefix_address] - 1)
        
def update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):
    # print "*********"
    # # print block_dup.get_start_address()
    # print falls_to
    # print pred_new
    print "*************"
    print block_dup.get_start_address()
    print falls_to

    #main path
    if path_idx != -1:
        new_falls_to = get_next_block_address(falls_to, idx_dict)
        block_dup.set_falls_to(new_falls_to)
        clone_block(falls_to,push_block, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)

    #out of main path
    else: #path_idx == -1
        if falls_to in path_to_clone: #it means that we have reach the main path, and we finish this clonning
            idx = get_idx(block_dup)
            new_falls_to = str(falls_to)+"_"+str(idx)
            update_idx_dict(idx,falls_to,idx_dict)
            block_dup.set_falls_to(new_falls_to)
            blocks_input[new_falls_to].add_origin(pred_new)

        else:
            if falls_to in locally_cloned: #bucle, actualizo
                idx = get_idx(block_dup)
                new_falls_to = str(falls_to)+"_"+str(idx)
                update_idx_dict(idx,falls_to,idx_dict)
                block_dup.set_falls_to(new_falls_to)
                blocks_input[new_falls_to].add_origin(pred_new)
            else:
                #clono
                idx = get_idx(block_dup)
                new_falls_to = str(falls_to)+"_"+str(idx)
                update_idx_dict(idx,falls_to,idx_dict)
                block_dup.set_falls_to(new_falls_to)
                clone_block(falls_to,push_block, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)


    print "++++++++++++++++++++++++"
    block_dup.display()
    print "++++++++++++++++++++++++"
    
    # if falls_to == 4431:
    #     print "HOLAAA"
    #     print count_block
    #     print count_pred
    #     print locally_cloned
    #     print path_to_clone
        
    # if (path_idx == -1) and (falls_to in locally_cloned):
    #     new_falls_to = find_sucessor_block(idx_dict, falls_to)
    #     # print "HOLA"
    #     # print new_falls_to
    #     block_dup.set_falls_to(new_falls_to)
    #     blocks_input[new_falls_to].add_origin(pred_new)
        
    # else:
    #     new_falls_to = get_next_block_address(falls_to, idx_dict)
    #     block_dup.set_falls_to(new_falls_to)
    #     clone_block(falls_to,push_block, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)


def update_idx_dict(idx,block,idx_dict):
    num = idx_dict.get(block,0)
    int_idx = int(idx)
    if num < int_idx:
        idx_dict[block] = int_idx
    
def clone_child(block_dup,jumps_to,falls_to,idx_dict,push_block,end_address,blocks_input,stack_out,globally_cloned,locally_cloned,path_to_clone, path_idx):
    t =  block_dup.get_block_type()
    pred_new = block_dup.get_start_address()
    
    if t == "conditional":
        if path_idx == -1:
            update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)

        else:
            if path_to_clone[path_idx] == jumps_to:
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            elif path_to_clone[path_idx] == falls_to:
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            else:
                raise Exception("Not consistent path")
            
    #Como los caminos no se actualizan, solo utilizamos el path_to_clone si el bloque incondicional
    #no ha sido clonado aun. En caso de haber sido clonado, ya hemos considerado un solo camino, y
    #por tanto nos podemos quedar directamente con quien hace el salto condicional.
    elif t == "unconditional":
        
        if path_idx != -1:

            # Se comprueba la condicion de solo tener un salto disponible (ya sea porque solo tenia
            # uno desde el principio, o se ha clonado y se ha quedado con uno)

            # print("Con jump:")
            # print jumps_to
            # print block_dup.get_list_jumps()
            
            if len(block_dup.get_list_jumps()) == 1:
                # print("He llegado con ")
                # print pred_new
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
            else:
                # print("Cojo el camino del path")
                update_jump_target(block_dup, path_to_clone[path_idx], idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
        else:
            #TODO: clonar todos los bloques que salen a partir de aqui por caminos separados
            if len(block_dup.get_list_jumps()) == 1:
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            else:
                print("Salto incondicional fuera del camino principal con varios destinos")
        
    elif t == "falls_to":
        if path_idx == -1:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
        else:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, push_block, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx + 1)


            
def clone_last_block(block_address, jump_address, blocks_input,idx_dict,locally_cloned, pred, push_address):
    global stack_index
    
    block = blocks_input[block_address]
    block_dup = block.copy()
    comes_from = block.get_comes_from()

    stack_in = stack_index[pred][1]
    stack_out = get_stack_evol(block_dup,stack_in)

    block_dup.set_stack_info((stack_in,stack_out))

    print("Copiando ultimo bloque:")
    print("Direccion de salto:")
    print jump_address

    # En este paso, se supone que block.get_start_address es necesariamente
    # un bloque inicial (probarlo)
    old_start_address = block.get_start_address()
    new_start_address = str(old_start_address) + "_" + str(idx_dict[old_start_address])
    idx_dict[old_start_address] += 1
    
    block_dup.set_start_address(new_start_address)
    stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
            
    block_dup.set_jump_target(jump_address,True) #By definition
    block_dup.set_list_jump([jump_address])
    #new_comes_from = update_comes_from(comes_from,idx,push_block,cloned)
    block_dup.add_origin(pred)

    #Nos quedamos con los caminos que han pasado por el push.
    paths_in = filter(lambda x: push_address  in x, block.get_paths())
    block_dup.set_paths(paths_in)

    #Del nodo original, quitamos los caminos que hacen ese push.
    paths_not_in = filter(lambda x: push_address not in x, block.get_paths())
    block.set_paths(paths_not_in)
    
    blocks_input[block_dup.get_start_address()]=block_dup

    blocks_input[jump_address].update_comes_from(new_start_address)
    
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

    index_dict = get_index_dict(blocks_input)

    for b in blocks_to_clone:
        clone(b, blocks_dict, address_dict, globally_cloned, index_dict)

    delete_old_blocks(globally_cloned, blocks_input)

    # print ("Copias")
    # print blocks_input['361_1'].get_list_jumps()
    # print blocks_input['361_1'].get_jump_target()
    # print blocks_input['361_1'].get_falls_to()
    show_graph(blocks_input)


def get_index_dict(blocks_input):
    index_dict = {}
    for address in blocks_input:
        index_dict[address] = 0
    return index_dict


def show_graph(blocks_input):
    for address in blocks_input:
        print("Bloque: ")
        print address
        print blocks_input[address].get_comes_from()
        print blocks_input[address].get_list_jumps()

def get_base_block(block):
    address = block.get_start_address()
    parts = address.split("_")
    base_address = parts[0]
    return int(base_address)

def get_idx(block):
    address = block.get_start_address()
    parts = address.split("_")
    idx = parts[1]
    return idx
