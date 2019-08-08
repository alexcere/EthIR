import opcodes
from utils import getLevel, get_initial_block_address, get_next_block_address
import os
from dot_tree import Tree, build_tree

def init():
    global cloned_blocks
    cloned_blocks = []

    global stack_index
    stack_index = {}

    global adress_dict
    address_dict = {}

    global first_push
    first_push = {}

    # Diccionario con clave, direccion del bloque que hace push
    # y valor el indice que le vamos a asociar al ultimo bloque a clonar.
    global last_block_idx_dict
    last_block_idx_dict = {}

    global first_copy
    first_copy = True

'''
Computes the inverse relation of address_dict, so that for each
push address, we know which is the furthest address reachable from there.
Multiple addresses can be reached when multiple pushes are done in the same block.
'''
def get_first_push(blocks_dict):
    global first_push
    global address_dict

    
    for final_address in address_dict:
        push_addresses = address_dict[final_address]
        for push_address in push_addresses:
            path = get_main_path(blocks_dict[final_address].get_paths(), push_address)
        
            if (push_address not in first_push) or (first_push[push_address] in path):
                first_push[push_address] = final_address


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


'''
Given the list of blocks, the final address of the path, the address of the block that pushes that final address
and the address of the block which needs to be copied, copies the whole path that goes across that block. Includes a flag indicating
whether this is first time last block is being copied. This is used in case there're several paths that end in the same final
address.
'''
def clone_path(blocks_dict, final_address, push_address, block_address, first_copy, globally_cloned, index_dict):
    global cloned_blocks
    global stack_index
    global last_block_idx_dict

    stack_in = stack_index[push_address][1]
    #print "EMPIEZA"

    #Empezamos a clonar desde los hijos del bloque que ha hecho el push
    #No se clona el bloque que ha hecho el push, asi que llamamos directamente
    #a clone_child.

    print("Push address")
    print push_address
    
    push_block_obj = blocks_dict[push_address]

    final_block_obj = blocks_dict[final_address]

    locally_cloned = []

    # Preguntamos el camino en el bloque que queremos la direccion final.
    # Si lo preguntasemos en block, podriamos quedarnos con caminos mas largos de los que
    # nos interesan, pues puede ser un bucle y pasar varias veces por ese camino.

    path_to_clone = find_path(blocks_dict, push_address, final_address)
    # path_to_clone = get_main_path(final_block_obj.get_paths(), push_address)
    print("Clonando")
    # print push_address
    print path_to_clone
    #modify_jump_first_block(push_block_obj,b,i)

    initial_jumps_to = push_block_obj.get_jump_target()

    # print initial_jumps_to

    initial_falls_to = push_block_obj.get_falls_to()

    #No vamos a separar el ultimo bloque del resto. Cuando lleguemos al final del todo,  
    clone_child(push_block_obj,initial_jumps_to, initial_falls_to,index_dict,block_address,blocks_dict,stack_in,globally_cloned,locally_cloned, path_to_clone, 1)
    
    
def clone_subpath(blocks_dict, final_address, push_address, pred_address, first_copy, globally_cloned, index_dict,last_address,locally_cloned):
    global cloned_blocks
    global stack_index
    global last_block_idx_dict

    stack_in = stack_index[push_address][1]
    #print "EMPIEZA"

    final_block_obj = blocks_dict[final_address]

    print("Ultima direccion")
    print final_address

    print last_address

    # Preguntamos el camino en el bloque que queremos la direccion final.
    # Si lo preguntasemos en block, podriamos quedarnos con caminos mas largos de los que
    # nos interesan, pues puede ser un bucle y pasar varias veces por ese camino.


    path_to_clone = find_path(blocks_dict, push_address, last_address)
    # path_to_clone = get_main_path(final_block_obj.get_paths(), push_address)

    # path_to_clone.append(last_address)
    print("Clonando camino secundario")
    # print push_address
    print path_to_clone
    #modify_jump_first_block(push_block_obj,b,i)

    #No vamos a separar el ultimo bloque del resto. Cuando lleguemos al final del todo,

    
    clone_block(push_address, final_address, blocks_dict, index_dict, stack_in, globally_cloned,locally_cloned,pred_address, path_to_clone, 1)

'''
Given a list of paths from the initial node to the node, and a
block address; finds a subpath that starts in that address. Error if 
not found a path with that address.
'''
def get_main_path(paths, address):
    for path in paths:
        if address in path:
            return path[path.index(address):]#TODO: Find start point and return it
    return []
    
    
def clone(block, blocks_input, globally_cloned, index_dict):
    global cloned_blocks
    global stack_index
    global address_dict
    global first_push
    global first_copy
    
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
            if (push_address not in globally_cloned) and (a == first_push[push_address]):
                clone_path(blocks_dict, a, push_address, block.get_start_address(), first_copy, globally_cloned, index_dict)
                first_copy = False
        i = i+1
        
    # El borrado se lleva a cabo una vez hemos hecho todo el cloning.


def clone_block(block_address, end_address, blocks_input, idx_dict, stack_in, globally_cloned,locally_cloned,pred, path_to_clone, path_idx):
    global stack_index
    global last_block_idx_dict
    # Comprobamos si no es el bloque final, o en caso de serlo, que el camino
    # se haya recorrido entero (puede repetirse este bucle final en el camino).
    if get_initial_block_address(block_address) != end_address or path_idx < len(path_to_clone) - 2:
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
        locally_cloned.append(get_initial_block_address(block_address))
        
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
        clone_child(block_dup,jumps_to,falls_to,idx_dict,end_address,blocks_input,stack_out,globally_cloned,locally_cloned, path_to_clone, path_idx)

        #block_dup.display()
       # block_dup.display()
        if block_address not in globally_cloned:
            globally_cloned.append(block_address)
    elif first_copy:
        last_block_idx_dict[end_address] = get_next_block_address(block_address,idx_dict)
        if end_address not in globally_cloned:
            globally_cloned.append(end_address)
        clone_last_block(block_address, path_to_clone[-1], blocks_input,idx_dict,locally_cloned, pred)
    else:
        blocks_input[last_block_idx_dict[end_address]].add_origin(pred) 
        
def update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):

    global address_dict

    possible_final_address = check_if_subpath(address_dict, jumps_to)

    # No clonamos si el bloque ya ha sido clonado y esta fuera del camino principal.
    if (get_initial_block_address(jumps_to) in locally_cloned) and (path_idx == -1):

        jump_address = find_sucessor_block(idx_dict, jumps_to)
        
        block_dup.set_jump_target(jump_address, True)
        block_dup.set_list_jump([jump_address])

        blocks_input[jump_address].add_origin(pred_new)

    elif (path_idx == -1) and (possible_final_address != -1):
        print("Camino no principal")
        
        new_jump_address = get_next_block_address(jumps_to, idx_dict)
        block_dup.set_jump_target(new_jump_address,True)
        block_dup.set_list_jump([new_jump_address])
        clone_subpath(blocks_input, end_address, jumps_to, pred_new, True, globally_cloned, idx_dict, path_to_clone[-1], locally_cloned)


    else:
        new_jump_address = get_next_block_address(jumps_to, idx_dict)
        block_dup.set_jump_target(new_jump_address,True)
        block_dup.set_list_jump([new_jump_address])

       # print block_dup.get_list_jumps()
        clone_block(jumps_to, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)

def find_sucessor_block(idx_dict, next_address):
    prefix_address = get_initial_block_address(next_address)
    return str(prefix_address) + "_" + str(idx_dict[prefix_address] - 1)

'''
Para comprobar si tengo que clonar un subcamino, veo directamente si la siguiente
direccion de salto esta en los valores del diccionario address_dict. En tal caso,
el nodo que sigue hace un push, y por tanto, necesito volver a considerar otro subcamino.
Devuelve el nodo al que hace el push la direccion de salto, en caso de hacerlo; o -1 en
caso contrario.
'''
def check_if_subpath(address_dict, push_node):
    for address in address_dict:
        if push_node in address_dict[address]:
            return address
    return -1


def update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx):

    global address_dict

    possible_final_address = check_if_subpath(address_dict, falls_to)
        
    if (path_idx == -1) and (get_initial_block_address(falls_to) in locally_cloned):
        new_falls_to = find_sucessor_block(idx_dict, falls_to)
        block_dup.set_falls_to(new_falls_to)
        blocks_input[new_falls_to].add_origin(pred_new)

    elif (path_idx == -1) and (possible_final_address != -1):
        print("Clonando camino no principal")
        new_falls_to = get_next_block_address(falls_to, idx_dict)
        block_dup.set_falls_to(new_falls_to)
        clone_subpath(blocks_input, end_address, falls_to, pred_new, True, globally_cloned, idx_dict, path_to_clone[-1], locally_cloned)
        
    else:
        new_falls_to = get_next_block_address(falls_to, idx_dict)
        block_dup.set_falls_to(new_falls_to)
        clone_block(falls_to, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx)


def clone_child(block_dup,jumps_to,falls_to,idx_dict,end_address,blocks_input,stack_out,globally_cloned,locally_cloned,path_to_clone, path_idx):
    t =  block_dup.get_block_type()
    pred_new = block_dup.get_start_address()
    if t == "conditional":
        if path_idx == -1:
            update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)

        else:
            if get_initial_block_address(path_to_clone[path_idx]) == get_initial_block_address(jumps_to):
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            elif get_initial_block_address(path_to_clone[path_idx]) == get_initial_block_address(falls_to):
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            else:
                print path_to_clone[path_idx]
                print falls_to
                print jumps_to
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
                print("He llegado con ")
                print pred_new
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
            else:
                print("Cojo el camino del path")
                update_jump_target(block_dup, path_to_clone[path_idx], idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1)
                
        else:
            #TODO: clonar todos los bloques que salen a partir de aqui por caminos separados
            if len(block_dup.get_list_jumps()) == 1:
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
            else:
                print("Salto incondicional fuera del camino principal con varios destinos")
                print pred_new
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
        
    elif t == "falls_to":
        if path_idx == -1:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
        else:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx + 1)


            
def clone_last_block(block_address, jump_address, blocks_input,idx_dict,locally_cloned, pred):
    global stack_index
    
    block = blocks_input[block_address]
    block_dup = block.copy()
    comes_from = block.get_comes_from()

    block_idx = get_next_block_address(block_address,idx_dict)

    stack_in = stack_index[pred][1]
    stack_out = get_stack_evol(block_dup,stack_in)

    block_dup.set_stack_info((stack_in,stack_out))

    print("Copiando ultimo bloque:")
    print("Direccion de salto:")
    print jump_address

    # En este paso, se supone que block.get_start_address es necesariamente
    # un bloque inicial (probarlo)
    new_start_address = block_idx
    idx_dict[get_initial_block_address(block_address)] += 1

    print("Nueva direccion inicial")
    print new_start_address
    block_dup.set_start_address(new_start_address)
    stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
            
    block_dup.set_jump_target(jump_address,True) #By definition
    block_dup.set_list_jump([jump_address])
    #new_comes_from = update_comes_from(comes_from,idx,push_block,cloned)
    block_dup.add_origin(pred)

    #Nos quedamos con los caminos que han pasado por el push.
    #paths_in = filter(lambda x: push_address  in x, block.get_paths())
    #block_dup.set_paths(paths_in)

    #Del nodo original, quitamos los caminos que hacen ese push.
    #paths_not_in = filter(lambda x: push_address not in x, block.get_paths())
    #block.set_paths(paths_not_in)
    
    blocks_input[block_dup.get_start_address()]=block_dup

    # blocks_input[jump_address].set_comes_from([new_start_address])

    # Anyadimos el nuevo origen, no podemos borrar el anterior porque puede
    # ocurrir que haya otros caminos que terminen este nodo, y necesiten
    # algun camino por el nodo inicial.
    blocks_input[jump_address].add_origin(new_start_address)

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
address_info: diccionario clave: push en la pila; valor: bloque que ha hecho ese push 
'''
def compute_cloning(blocks_to_clone,blocks_input,stack_info, address_info):
    global stack_index
    global address_dict
    
    init()
    blocks_dict = blocks_input
    stack_index = stack_info
    address_dict = address_info

    globally_cloned = []

    get_first_push(blocks_dict)

    index_dict = get_index_dict(blocks_input)

    for b in blocks_to_clone:
        clone(b, blocks_dict, globally_cloned, index_dict)

    #delete_old_blocks(globally_cloned, blocks_input)

    # print ("Copias")
    # print blocks_input['361_1'].get_list_jumps()
    # print blocks_input['361_1'].get_jump_target()
    # print blocks_input['361_1'].get_falls_to()
    # show_graph(blocks_input)


def get_index_dict(blocks_input):
    index_dict = {}
    for address in blocks_input:
        index_dict[address] = 0
    return index_dict



def show_graph(blocks_input):
    for address in blocks_input:
        print("Bloque: ")
        print address
        print("Comes from: ")
        print blocks_input[address].get_comes_from()
        print("List jump: ")
        print blocks_input[address].get_list_jumps()


def find_path(blocks_dict, push_address, final_address):
    current_paths = [(final_address, [final_address])]
    idx = 0
    while True:
        current_address, current_path = current_paths[idx]
        current_block = blocks_dict[current_address]
        paths = current_block.get_paths()
        path_to_push = get_main_path(paths, push_address)
        print("Buscando camino...")
        print current_path
        print current_address
        print path_to_push
        print push_address
        print final_address
        print idx
        print current_block.get_comes_from()
        if path_to_push != []:
            return path_to_push[:-1] + current_path
        else:
            for item in current_block.get_comes_from():
                current_paths.append((item, [item] + current_path))
            idx = idx + 1
