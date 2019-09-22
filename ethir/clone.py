import opcodes

from utils import getLevel, get_initial_block_address, get_next_block_address, check_if_not_cloned_address, get_idx_from_address, show_graph

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

    global not_already_cloned_node_found
    not_already_cloned_node_found = True
    

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

    # locally_cloned = []
    
    # Preguntamos el camino en el bloque que queremos la direccion final.
    # Si lo preguntasemos en block, podriamos quedarnos con caminos mas largos de los que
    # nos interesan, pues puede ser un bucle y pasar varias veces por ese camino.

    # path_to_clone = find_path(blocks_dict, push_address, final_address)

    # We are interested in paths that start in push_address, therefore
    # we are going to shorten them and filter the ones that don't contain
    # that address.
    
    all_possible_paths = map(lambda x: get_shortened_path(x,push_address), final_block_obj.get_paths())

    filtered_paths = filter(lambda x: x != [], all_possible_paths)

    paths_to_clone = filter_paths_by_concurring_inconditional_nodes(filtered_paths, blocks_dict)

    # print(all_possible_paths)
    # print(filtered_paths)
    print("+++++++++++++++++++++++++++++")
    print("Diccionario con clases de equivalencia")
    print(paths_to_clone)

    for tuple_to_clone in paths_to_clone.values():

        locally_cloned = []

        path_to_clone = list(tuple_to_clone)
        
        # path_to_clone = get_main_path(final_block_obj.get_paths(), push_address)
        print("Clonando")
        # print push_address
        print path_to_clone
        #modify_jump_first_block(push_block_obj,b,i)

        initial_jumps_to = push_block_obj.get_jump_target()

        # print initial_jumps_to

        initial_falls_to = push_block_obj.get_falls_to()

        # As I need a list of the same length of path_to_clone, I just copy it and use it as path_to_clone_idx  
        clone_child(push_block_obj,initial_jumps_to, initial_falls_to,index_dict,block_address,blocks_dict,stack_in,globally_cloned,locally_cloned, path_to_clone, 1, path_to_clone[:], 1)

        first_copy = False
    

def clone_subpath(blocks_dict, last_address, push_address, pred_address, first_copy, globally_cloned, index_dict, locally_cloned):
    global cloned_blocks
    global stack_index
    global last_block_idx_dict

    stack_in = stack_index[push_address][1]
    #print "EMPIEZA"

    locally_cloned = []
    
    # Preguntamos el camino en el bloque que queremos la direccion final.
    # Si lo preguntasemos en block, podriamos quedarnos con caminos mas largos de los que
    # nos interesan, pues puede ser un bucle y pasar varias veces por ese camino.

    # path_to_clone = find_path(blocks_dict, push_address, last_address)

    # We are interested in paths that start in push_address, therefore
    # we are going to shorten them and filter the ones that don't contain
    # that address.
    
    all_possible_paths = map(lambda x: get_shortened_path(x,push_address) , blocks_dict[last_address].get_paths())

    filtered_paths = filter(lambda x: x != [], all_possible_paths)
    
    # print("+++++++++++++++++++++++++++++")
    # print("Diccionario con clases de equivalencia")
    # print(filter_paths_by_concurring_inconditional_nodes(filtered_paths, blocks_dict))

    paths_to_clone = filter_paths_by_concurring_inconditional_nodes(filtered_paths, blocks_dict)

    for path_to_clone in paths_to_clone.values():

        # We need the before-last address in order to do the cloning properly
        block_to_clone_address = path_to_clone[-2]

        print("Clonando camino secundario")
        # print push_address
        print path_to_clone
        #modify_jump_first_block(push_block_obj,b,i)

        #No vamos a separar el ultimo bloque del resto. Cuando lleguemos al final del todo,
    
        clone_block(push_address, block_to_clone_address, blocks_dict, index_dict, stack_in, globally_cloned,locally_cloned,pred_address, path_to_clone, 1, path_to_clone[:], 1)

'''
Given a list of paths from the initial node to the node, and a
block address; finds a subpath that starts in that address. Error if 
not found a path with that address.
'''
def get_main_path(paths, address):
    for path in paths:
        if address in path:
            return path[path.index(address):]
    return []

def get_shortened_path(path, push_address):
    if push_address in path:
        return path[path.index(push_address):]
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
            #if (push_address not in globally_cloned) and (a == first_push[push_address]):
            if a == first_push[push_address]:
                clone_path(blocks_dict, a, push_address, block.get_start_address(), first_copy, globally_cloned, index_dict)
                first_copy = False
        i = i+1
        
    # El borrado se lleva a cabo una vez hemos hecho todo el cloning.


def clone_block(block_address, end_address, blocks_input, idx_dict, stack_in, globally_cloned,locally_cloned,pred, path_to_clone, path_idx, path_to_clone_idx, current_block_idx):
    global stack_index
    global last_block_idx_dict

    # Comprobamos si no es el bloque final, o en caso de serlo, que el camino
    # se haya recorrido entero (puede repetirse este bucle final en el camino).
    if get_initial_block_address(block_address) != end_address or path_idx < len(path_to_clone) - 2:
    #if block_address != end_address and block_address not in locally_cloned:


        print("Nombre antiguo")
        print block_address
        block = blocks_input[block_address]
        comes_from_old = block.get_comes_from()
        #TODO: quizas actualizar el comes from del bloque que no se va a borrar.
        
        block_dup = block.copy()
        stack_out = get_stack_evol(block_dup,stack_in)
        block_dup.set_stack_info((stack_in,stack_out))

        old_start_address = block.get_start_address()

        new_start_address = get_next_block_address(old_start_address,idx_dict)

        idx_dict[get_initial_block_address(old_start_address)] += 1

        print "NEW START ADDRESS HERE"
        print new_start_address
        
        block_dup.set_start_address(new_start_address)
        stack_index[block_dup.get_start_address()] = [stack_in,stack_out]
        
        jumps_to = block_dup.get_jump_target()
        falls_to = block_dup.get_falls_to()

        locally_cloned.append(block_address)

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
        clone_child(block_dup,jumps_to,falls_to,idx_dict,end_address,blocks_input,stack_out,globally_cloned,locally_cloned, path_to_clone, path_idx, path_to_clone_idx, current_block_idx)

        #locally_cloned only keeps the current execution path that leads to clone things
        # locally_cloned.pop()

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
        
def update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx):

    global address_dict

    possible_final_address = check_if_subpath(address_dict, jumps_to)

    if path_idx != -1:
        new_jump_address = get_next_block_address(jumps_to, idx_dict)
        block_dup.set_jump_target(new_jump_address,True)
        block_dup.set_list_jump([new_jump_address])

        path_to_clone_idx[path_idx] = get_idx_from_address(new_jump_address)
        # print block_dup.get_list_jumps()
        clone_block(jumps_to, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx)

    else:

        if jumps_to in locally_cloned:
            new_jumps_to = find_next_node_address_already_cloned(path_to_clone, path_to_clone_idx, current_block_idx, jumps_to)
            block_dup.set_jump_target(new_jumps_to, True)
            block_dup.set_list_jump([new_jumps_to])

            blocks_input[new_jumps_to].add_origin(pred_new)

        elif possible_final_address != -1:
            new_jump_address = get_next_block_address(jumps_to, idx_dict)
            block_dup.set_jump_target(new_jump_address,True)
            block_dup.set_list_jump([new_jump_address])
        
            clone_subpath(blocks_input, possible_final_address, jumps_to, pred_new, True, globally_cloned, idx_dict, locally_cloned)
        else:
            new_jump_address = get_next_block_address(jumps_to, idx_dict)
            block_dup.set_jump_target(new_jump_address,True)
            block_dup.set_list_jump([new_jump_address])

            # print block_dup.get_list_jumps()
            clone_block(jumps_to, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx)
        

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


def update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx):

    global address_dict

    possible_final_address = check_if_subpath(address_dict, falls_to)

    # main path: we keep on cloning, even though we may
    # repit a node already cloned
    if path_idx != -1:
        new_falls_to = get_next_block_address(falls_to, idx_dict)
        block_dup.set_falls_to(new_falls_to)

        path_to_clone_idx[path_idx] = get_idx_from_address(new_falls_to)
        
        clone_block(falls_to, end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx)

    #out of main path: several different cases
    else:
        # If we've already cloned next node, we find the corresponding
        # index of that node, and add current node to its comes_from list

        if falls_to in locally_cloned:
            new_falls_to = find_next_node_address_already_cloned(path_to_clone, path_to_clone_idx, current_block_idx, falls_to)
            blocks_input[new_falls_to].add_origin(pred_new)
            block_dup.set_falls_to(new_falls_to)
            
        elif possible_final_address != -1:
            new_falls_to = get_next_block_address(falls_to, idx_dict)
            block_dup.set_falls_to(new_falls_to)
            clone_subpath(blocks_input, possible_final_address, falls_to, pred_new, True, globally_cloned, idx_dict, locally_cloned)

        else:
            new_falls_to = get_next_block_address(falls_to, idx_dict)
            block_dup.set_falls_to(new_falls_to)
            clone_block(falls_to,end_address,blocks_input,idx_dict,stack_out,globally_cloned,locally_cloned,pred_new, path_to_clone, path_idx, path_to_clone_idx, current_block_idx)

''' If we know a child has already been cloned, we need to find out which address would corresponds to that node, as it might have been cloned several times in current path.'''
def find_next_node_address_already_cloned(path_to_clone, path_to_clone_idx, current_block_idx, block_address):
    base_address = get_initial_block_address(block_address)

    # For finding the corresponding index, I need to find the first match in path_to_clone with my base address.
    # But be aware, I have to start searching from current_block_idx, so in order to find this index, I
    # take my list from that index, find the base_address and then add current_block_idx, as the index returned
    # starts in current_block_idx
    already_cloned_idx = path_to_clone[current_block_idx:].index(base_address) + current_block_idx

    new_block_address =  str(base_address) + "_" +  str(path_to_clone_idx[already_cloned_idx])

    return new_block_address

def clone_child(block_dup,jumps_to,falls_to,idx_dict,end_address,blocks_input,stack_out,globally_cloned,locally_cloned,path_to_clone, path_idx, path_to_clone_idx, current_block_idx):
    t =  block_dup.get_block_type()
    pred_new = block_dup.get_start_address()
    if t == "conditional":
        if path_idx == -1:
            update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, current_block_idx)
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, current_block_idx)

        else:
            if path_to_clone[path_idx] == get_initial_block_address(jumps_to):
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1, path_to_clone_idx, path_idx+1)
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, path_idx)
            elif path_to_clone[path_idx] == get_initial_block_address(falls_to):
                update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1, path_to_clone_idx, path_idx+1)
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, path_idx)
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
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1, path_to_clone_idx, path_idx+1)
                
            else:
                print("Cojo el camino del path")
                update_jump_target(block_dup, path_to_clone[path_idx], idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx+1, path_to_clone_idx, path_idx+1)
                
        else:
            #TODO: clonar todos los bloques que salen a partir de aqui por caminos separados
            if len(block_dup.get_list_jumps()) == 1:
                update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, current_block_idx)
            else:
                print("Salto incondicional fuera del camino principal con varios destinos")
                print pred_new
                raise Exception("Cloning unconditional node out of main path")
                # update_jump_target(block_dup, jumps_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1)
        
    elif t == "falls_to":
        if path_idx == -1:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, -1, path_to_clone_idx, current_block_idx)
        else:
            update_falls_to(block_dup, falls_to, idx_dict, locally_cloned, end_address, blocks_input, stack_out, globally_cloned, pred_new, path_to_clone, path_idx + 1, path_to_clone_idx, path_idx + 1)


            
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

    # print("Graph consistent:")
    # print(check_graph_consistency(blocks_input))

    print(address_info)    
    get_first_push(blocks_dict)

    global first_push
    print(first_push)

    print("All paths")
    show_paths(blocks_input)

    index_dict = get_index_dict(blocks_input)

    for b in blocks_to_clone:
        print("Hay que clonar")
        print(b.get_start_address())
        clone(b, blocks_dict, globally_cloned, index_dict)

    #delete_old_blocks(globally_cloned, blocks_input)

    visited_blocks = calculate_comes_from(blocks_input)

    # We have to delete non-visited blocks
    blocks_to_delete = set(blocks_input.keys()).difference(set(visited_blocks))
    
    delete_old_blocks(blocks_to_delete, blocks_input)
    
    print("Graph consistent:")
    print(check_graph_consistency(blocks_input))

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
        if path_to_push != [] and check_if_consistent_path(path_to_push[:-1] + current_path):
            return path_to_push[:-1] + current_path
        else:
            for item in current_block.get_comes_from():
                if check_if_not_cloned_address(item) and check_if_consistent_address(current_path, item):
                    current_paths.append((item, [item] + current_path))
            idx = idx + 1

'''
Returns false if current_address makes a push and that push is not in current path, otherwise true.
'''
def check_if_consistent_address(current_path, current_address):
    global first_push

    if current_address in first_push:
        print("Posible candidato")
        print current_address
        print first_push[current_address]
        print current_path

    return not((current_address in first_push) and (first_push[current_address] not in current_path))


def check_if_consistent_path(path):
    print("Comprobando camino")
    for i in range(len(path) - 1):
        if not(check_if_consistent_address(path[i:], path[i])):
            return False
    return True

''' Given a node and where it comes from, checks all relevant info is consistent'''
def check_node_consistency(blocks_dict, initial_address, comes_from_address, visited_nodes):
    
    current_block = blocks_dict[initial_address]

    comes_from = current_block.get_comes_from()

    # List containing all the values checked
    conds = []
    
    # Always same condition: check if previous block is in comes_from list
    conds.append(comes_from_address in comes_from)
    
    if initial_address not in visited_nodes:
        
        t = current_block.get_block_type()

        jumps_to = current_block.get_jump_target()
        falls_to = current_block.get_falls_to()

        visited_nodes.append(initial_address)

        # Conditional jump: check comes_from + falls to node + jump target node
        if t == "conditional":

            conds.append(check_node_consistency(blocks_dict,falls_to, initial_address,visited_nodes))
            conds.append(check_node_consistency(blocks_dict,jumps_to, initial_address,visited_nodes))

            print("conditional check")

       # Unconditional jump : check length of jump list + comes_from + 
       # jumps target is the element of jump list + jump target node +
       # falls_to == None
        elif t == "unconditional":

            jump_list = current_block.get_list_jumps()
            
            conds.append(len(jump_list) == 1)
            conds.append(jumps_to in jump_list)
            conds.append(check_node_consistency(blocks_dict,jumps_to, initial_address, visited_nodes))
            conds.append(falls_to == None)
            print("Falls_to")
            print(falls_to)

            print("unconditional check")
        
        # Falls to node: check comes_from + next_node + jumps_to == None
        elif t == "falls_to":
            
            conds.append(check_node_consistency(blocks_dict, falls_to, initial_address, visited_nodes))
            conds.append(jumps_to == 0)

            print("Jumps to")
            print(jumps_to)

            print("falls to check")
            
        # Terminal node: only check comes_from

        else:
            print("terminal node to check")
        
    # If visited, as we've checked that node before, we just need to make sure
    # comes_from has current node.

    else:
        print("already checked")
    print(initial_address)
    print(conds)
    return reduce(lambda i,j: i and j, conds)

''' Given a dictionary containing all blocks from graph, checks if all the info
is coherent '''
def check_graph_consistency(blocks_dict, initial_address = 0):
    visited_nodes = [initial_address]
    initial_block = blocks_dict[initial_address]

    t = initial_block.get_block_type()

    jumps_to = initial_block.get_jump_target()
    falls_to = initial_block.get_falls_to()

    conds = []

    # Conditional jump: call check_node with falls_to && jump_target && all visited nodes are blocks
    # are the ones in block_dict
    if t == "conditional":
         
         conds.append(check_node_consistency(blocks_dict,falls_to, initial_address,visited_nodes))
         conds.append(check_node_consistency(blocks_dict,jumps_to, initial_address,visited_nodes))
         
         print("initial node: conditional")
         
    # Unconditional jump : check length of jump list && comes_from && 
    # jumps target is the element of jump list && jump target node &&
    # falls_to == None
    elif t == "unconditional":
         
         jump_list = current_block.get_list_jumps()
         
         conds.append(len(jumps_list) == 1)
         conds.append(jumps_to in jump_list)
         conds.append(check_node_consistency(blocks_dict,jumps_to, initial_address, visited_nodes))
         conds.append(falls_to == None)

         print("initial node: unconditional")
         
    # Falls to node: visited nodes == blocks_dict.keys && check  next_node  && jumps_to == None
    elif t == "falls_to":
        
         conds.append(check_node_consistency(blocks_dict, falls_to, initial_address, visited_nodes))
         conds.append(jumps_to == 0)
         
         print("initial node: falls to")
         
    # Terminal node: only check there's no other block
    else:
         
         print("initial Node: terminal node")

    # Check all visited nodes are the same in the dictionary
    conds.append(visited_nodes.sort() == blocks_dict.keys().sort())

    print(conds)
    
    return reduce(lambda i,j: i and j, conds)


''' Given a node and where it comes from, updates info from comes_from'''
def calculate_comes_from_node(blocks_dict, initial_address, comes_from_address, visited_nodes):

    print(initial_address)
    
    current_block = blocks_dict[initial_address]
    
    if initial_address not in visited_nodes:
        
        t = current_block.get_block_type()

        jumps_to = current_block.get_jump_target()
        falls_to = current_block.get_falls_to()

        visited_nodes.append(initial_address)

        current_block.set_comes_from([comes_from_address])
        
        # Conditional jump: update jumps_to and falls_to
        if t == "conditional":
            print("+++ Changing comes_from from conditional node +++")
            calculate_comes_from_node(blocks_dict,falls_to, initial_address,visited_nodes)
            calculate_comes_from_node(blocks_dict,jumps_to, initial_address,visited_nodes)
            
       # Unconditional jump : update jumps_to
        elif t == "unconditional":
            print("+++ Changing comes_from from inconditional node +++")
            calculate_comes_from_node(blocks_dict,jumps_to, initial_address, visited_nodes)
            
        # Falls to node: update falls_to
        elif t == "falls_to":
            print("+++ Changing comes_from from falls_to node +++")
            calculate_comes_from_node(blocks_dict, falls_to, initial_address, visited_nodes)
        
        # Terminal node: nothing to change
        
    # If visited, as we've checked that node before, we just add new address to comes_from
    else:
        current_block.add_origin(comes_from_address)

        
''' Given a dictionary with all graph info, and an initial address (by default, 0),
updates comes_from info for each node reachable from 0.
Returns a list with all visited nodes'''
def calculate_comes_from(blocks_dict, initial_address = 0):
    visited_nodes = [initial_address]
    initial_block = blocks_dict[initial_address]

    t = initial_block.get_block_type()

    jumps_to = initial_block.get_jump_target()
    falls_to = initial_block.get_falls_to()
    
    # Conditional jump: update comes_from from both falls_to and jumps_to 
    if t == "conditional":
         print("initial node comes from: conditional")
         calculate_comes_from_node(blocks_dict,falls_to, initial_address,visited_nodes)
         calculate_comes_from_node(blocks_dict,jumps_to, initial_address,visited_nodes)

    # Unconditional jump: update comes_from from just jumps_to
    elif t == "unconditional":
         print("initial node comes from: unconditional")
         calculate_comes_from_node(blocks_dict,jumps_to, initial_address, visited_nodes)
         
    # Falls to node: update comes_from from just falls_to
    elif t == "falls_to":
         print("initial node comes from: falls to")
         calculate_comes_from_node(blocks_dict, falls_to, initial_address, visited_nodes)
        
    # Terminal node: nothing to do

    return visited_nodes


# For debugging
def show_paths(blocks_dict):
    for block in blocks_dict:
        print("Block paths: " + str(block))
        print(blocks_dict[block].get_paths())

''' Given paths with the same beginning and end and info from nodes, finds different equivalence classes and stores a representant for each of them. Two paths are considered equivalent if they share the same inconditional nodes with various jumps in the same order.'''
def filter_paths_by_concurring_inconditional_nodes(paths, blocks_dict):
    equivalence_classes = {}
    for path in paths:
        standard_representation = tuple(obtain_standard_representation(path, blocks_dict))
        if standard_representation not in equivalence_classes:
            equivalence_classes[standard_representation] = path

    return equivalence_classes
        



''' Given a path and info from nodes, obtains all inconditional nodes with varios jumps from path. '''
def obtain_standard_representation(path, blocks_dict):
    new_representation = []
    for address in path:
        block = blocks_dict[address]
        t = block.get_block_type()
        list_jumps = block.get_list_jumps()
        if (t == "unconditional") and (len(list_jumps) > 1):
            new_representation.append(address)
    return new_representation

    
