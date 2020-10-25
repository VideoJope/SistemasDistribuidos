import socket
import sys
import multiprocessing
import hashlib

def main():

    m = int(input("Insira a quantidade 'm' de bits de identificador (2^m nós popularão o Chord): "))

    #Inicializa os processos dos nos Chord:
    for i in range(2 ** m):
        nodeProcess = multiprocessing.Process(target = node, args = (i, m))
        nodeProcess.start()

    print("\nChord inicializado! Aguardando requisicoes de clientes.\n")

    #Inicializa seu socket de servidor para responder requisicoes de clientes sobre o endereco de nos iniciais: 
    mainSocket = socket.socket()
    mainSocket.bind(('', 4999)) #endereco conhecido pelo cliente

    #Loop principal respondera consultas de clientes sobre o endereco de nos inicias: 
    while True:
        mainSocket.listen(5)
        clientSocket, addr = mainSocket.accept()
        startingNodeIDstring = receiveFrom(clientSocket)
        nodeAddr = getNodeAddr(startingNodeIDstring)
        sendTo(nodeAddr, clientSocket)
        clientSocket.close()


def getNodeAddr(startingNodeIDstring):
    startingNodeID = int(startingNodeIDstring)
    return "localhost," + str(5000 + startingNodeID) #para implementacoes mais complexas, uma tabela contendo o endereco de possiveis nos iniciais seria consultada aqui 


def node(id, mbits):
    port = 5000 + id #port do node atual (sempre definido como id_do_node + 5000)
    finger = populateFingerTable(id, mbits) #popula a tabela finger com os ports dos demais nodes alcancaveis pelo node atual
    data = {} #dicionario que contera os pares de chave e valor armazenados localmente no node

    #Inicializacao do socket:
    nodeSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    nodeSocket.bind(('', port))
    
    while True:
        nodeSocket.listen(5)
        incSocket, addr = nodeSocket.accept()
        message = receiveFrom(incSocket)
        incSocket.close()
        #Insercao:
        if message.split(' ')[0] == 'i':
            insere(message, data, finger, id, mbits)
        #Busca:
        elif message.split(' ')[0] == 's':
            busca(message, data, finger, id, mbits)


def insere(message, data, finger, nodeID, mbits):
    #'message' vai estar no formato: "i [key] [value] [clientHostName],[clientPort]" se ela originar do cliente
    #'message' vai estar no formato: "i [key] [value] [clientHostName],[clientPort] [hashedKey]" se ela originar de outro node ([hashedKey] e obtido atraves da chamada de funcao hash([key]))

    splitMessage = message.split(' ')

    #Realiza o hash da chave caso a mensagem tenha se originado do cliente:
    if len(splitMessage) == 4:
        hashedKey = hash(splitMessage[1], mbits)
        splitMessage.append(hashedKey)
        message = splitMessage[0] + " " + splitMessage[1] + " " + splitMessage[2] + " " + splitMessage[3] + " " + splitMessage[4]
        print("Requisicao de insercao chegou ao node de id: " + str(nodeID))
    
    key = splitMessage[1]
    value = splitMessage[2]
    hashedKeyInt = int(splitMessage[4])
    
    clientAddr = (splitMessage[3].split(',')[0], int(splitMessage[3].split(',')[1]))

    #Se hash da chave estiver entre o predecessor e o node atual, inclui o par chave-valor em data e retorna uma resposta ao cliente:
    predecessorNodeID = finger[0] - 5000 #como os ports reservados sao 5000 + id_do_no, podemos obter o ids dos nos apartir dos ports contidos em finger
    if belongsToChordInterval(hashedKeyInt, predecessorNodeID, nodeID, mbits) or hashedKeyInt == nodeID: 
        data[key] = value
        #Responde ao cliente que o par chave,valor foi inserido com sucesso:
        responseSocket = socket.socket()
        responseSocket.connect(clientAddr)
        returnMessage = "(Chave, Valor) : (" + key + ", " + value + ")  Inserido com sucesso no node de ID " + str(nodeID)
        sendTo(returnMessage, responseSocket)
        responseSocket.close()
        print(returnMessage + '\n')
        return
    else:
    #Caso contrario, percorrer finger ate encontrar o primeiro node precedente ao hash da chave:
        for k in range(mbits, 0, -1):
            fingerMemberID = finger[k] - 5000
            if belongsToChordInterval(fingerMemberID, nodeID, hashedKeyInt, mbits) or hashedKeyInt == fingerMemberID:
                #Envia uma requisicao de insercao ao primeiro node precedente ao hash da chave contido em finger:
                responseSocket = socket.socket()
                responseSocket.connect(('', finger[k]))
                sendTo(message, responseSocket)
                responseSocket.close()
                print("Requisicao de insercao passada adiante para o node de id: " + str(fingerMemberID))
                return
        #Responde ao cliente que nao foi possivel inserir o par chave,valor:
        responseSocket = socket.socket()
        responseSocket.connect(clientAddr)
        sendTo("ERRO! Nao foi possivel inserir o par chave,valor.", responseSocket)
        responseSocket.close()
        print("ERRO! Nao foi possivel inserir o par chave,valor.\n")
    return


def busca(message, data, finger, nodeID, mbits):
    #'message' vai estar no formato: "s [key] [clientHostName],[clientPort]" se ela originar do cliente
    #'message' vai estar no formato: "s [key] [clientHostName],[clientPort] [hashedKey]" se ela originar de outro node ([hashedKey] e obtido atraves da chamada de funcao hash([key]))

    splitMessage = message.split(' ')

    #Realiza o hash da chave caso a mensagem tenha se originado do cliente:
    if len(splitMessage) == 3:
        hashedKey = hash(splitMessage[1], mbits)
        splitMessage.append(hashedKey)
        message = splitMessage[0] + " " + splitMessage[1] + " " + splitMessage[2] + " " + splitMessage[3]
        print("Requisicao de busca chegou ao node de id: " + str(nodeID))

    key = splitMessage[1]
    hashedKeyInt = int(splitMessage[3])

    clientAddr = (splitMessage[2].split(',')[0], int(splitMessage[2].split(',')[1]))

    #Se hash da chave estiver entre o predecessor e o node atual, verifica se a chave esta presente em data e retorna a resposta ao cliente:
    predecessorNodeID = finger[0] - 5000 #como os ports reservados sao 5000 + id_do_no, podemos obter o ids dos nos apartir dos ports contidos em finger
    if belongsToChordInterval(hashedKeyInt, predecessorNodeID, nodeID, mbits) or hashedKeyInt == nodeID: 
        if key in data.keys():
            returnMessage = "A chave '" + key + "' de valor '" + data[key] + "' se encontra armazenada no node de ID " + str(nodeID)
        else:
            returnMessage = "A chave requisitada nao se encontra presente no sistema."
        #Responde ao cliente o resultado da busca:
        responseSocket = socket.socket()
        responseSocket.connect(clientAddr)
        sendTo(returnMessage, responseSocket)
        responseSocket.close()
        print(returnMessage + '\n')
        return
    else:
    #Caso contrario, percorrer finger ate encontrar o primeiro node precedente ao hash da chave:
        for k in range(mbits, 0, -1):
            fingerMemberID = finger[k] - 5000
            if belongsToChordInterval(fingerMemberID, nodeID, hashedKeyInt, mbits) or hashedKeyInt == fingerMemberID:
                #Envia uma requisicao de busca ao primeiro node precedente ao hash da chave contido em finger:
                responseSocket = socket.socket()
                responseSocket.connect(('', finger[k]))
                sendTo(message, responseSocket)
                responseSocket.close()
                print("Requisicao de busca passada adiante para o node de id: " + str(fingerMemberID))
                return
        #Responde ao cliente que nao foi possivel inserir o par chave,valor:
        responseSocket = socket.socket()
        responseSocket.connect(clientAddr)
        sendTo("ERRO! Nao foi possivel buscar a chave requisitada.", responseSocket)
        responseSocket.close()
        print("ERRO! Nao foi possivel buscar a chave requisitada.\n")
    return


#A funcao hash abaixo aplica a funcao hash MD5 na string [key] passada como parametro, retornando uma string contendo o inteiro que representa o id da chave no Chord:
def hash(keyString, mbits):
    hash_object = hashlib.md5(keyString.encode())
    hash_int = int.from_bytes(hash_object.digest(), "little") % 2**mbits #modulo 2^m para representar o id da chave no Chord
    hashedKey = str(hash_int)
    return hashedKey


#Retorna True se 'element' pertence a (intervalStart, intervalEnd) em um Chord com 2^mbits de comprimento:
def belongsToChordInterval(element, intervalStart, intervalEnd, mbits):
    i = (intervalStart + 1) % 2**mbits
    while i != intervalEnd:
        if i == element:
            return True
        else:
            i = (i + 1) % 2**mbits
    return False


def populateFingerTable(id, mbits):
    #Note que a tabela finger nao contera o endereco completo para o node, somente sua porta designada.
    #Isso nao sera um problema ja que todos os nos estao disponiveis no mesmo IP.
    finger = []
    finger.append((id - 1) % 2**mbits + 5000)               #finger[0] nao existe na proposta descrita no artigo, aqui estamos ocupando essa posicao da lista com a porta do node predecessor ao atual
    for k in range(1, mbits + 1):
        finger.append((id + 2**(k-1)) % 2**mbits + 5000)    #finger[k], para 1 <= k <= m, contera a porta do node de identificador (id_do_node_atual + 2^k-1)mod2^m como descrito no artigo
    return finger



#Envia a mensagem (passada por parametro como string) ao socket do cliente apos adequa-la ao protocolo estabelecido:
def sendTo(messageString, targetSocket):
    messageLength = len(messageString)
    if messageLength > 9999:
        messageString = messageString[:9999] #caso a mensagem ultrapasse o limite de 9999 caracteres, remove os caracteres extras
        messageLength = 9999
    #Header no formato "XXXX:", com os 4 Xs sendo digitos representando o tamanho da mensagem que segue os dois pontos:
    header = '0' * (4 - len(str(messageLength))) + str(messageLength) + ':'
    messageString = header + messageString #concatena o header com a mensagem a ser enviada
    message = messageString.encode('utf-8')
    return targetSocket.sendall(message)


#Recebe uma mensagem do socket passado como parametro, a retornando no formato de string:
def receiveFrom(incSocket):
    #Recebe o Header contendo o tamanho da Mensagem a ser lida:
    numberBytesRead = 0
    dataChunks = []
    while numberBytesRead < 5:
        data = incSocket.recv(5 - numberBytesRead)
        if not data: return False
        dataChunks.append(data)
        numberBytesRead = numberBytesRead + len(data)
    header = str(b''.join(dataChunks), encoding = 'utf-8')
    if(header[-1] != ':'): return False

    messageLength = int(header[:4]) #tamanho da mensagem, obtido apartir do header

    #Recebe a Mensagem:
    numberBytesRead = 0
    dataChunks = []
    while numberBytesRead < messageLength:
        data = incSocket.recv(min(messageLength - numberBytesRead, 1024))
        if not data: return False
        dataChunks.append(data)
        numberBytesRead = numberBytesRead + len(data)
    message = str(b''.join(dataChunks), encoding = 'utf-8')

    return message


main()