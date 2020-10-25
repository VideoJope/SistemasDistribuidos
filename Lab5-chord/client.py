import socket
import sys

def main():

    print("\nBem-vindo(a)! Digite help para uma lista de comandos.")

    while True:

        command = input("\nComando: ")
        splitCommand = command.split(' ')

        #Comando Help:
        if splitCommand[0] == 'help':
            print("\nComandos disponiveis:")
            print("help - Imprime esta mensagem.")
            print("search [startingNodeID] [key] - Retorna o valor associado a chave [key] no sistema, partindo do node de ID [startingNodeID].")
            print("insert [startingNodeID] [key] [value] - Insere no sistema o par chave, valor ([key], [value]) em seu node adequado, partindo do node de ID [startingNodeID].")
            print("quit - Fecha a aplicacao cliente.\n")

        #Comando Busca:
        elif splitCommand[0] == 'search':
            if len(splitCommand) != 3:
                print("Comando deve estar no formato: find [startingNodeID] [key]")
            else:
                startingNodeID = str(abs(int(splitCommand[1])))
                key = splitCommand[2]
                returnString = busca(startingNodeID, key)
                print(returnString)

        #Comando Insercao:
        elif splitCommand[0] == 'insert':
            if len(splitCommand) != 4:
                print("Comando deve estar no formato: insert [startingNodeID] [key] [value]")
            else:
                startingNodeID = str(abs(int(splitCommand[1])))
                key = splitCommand[2]
                value = splitCommand[3]
                returnString = insere(startingNodeID, key, value)
                print(returnString)

        #Comando de Saida:
        elif splitCommand[0] == 'quit' or splitCommand[0] == 'exit':
            print("Fechando aplicacao cliente.")
            break

        #Comando Invalido:
        else:
            print("Comando invalido.")



def insere(startingNodeID, key, value):

    #Requisita ao programa principal o endereco do node de ID startingNodeID:
    nodeAddr = getInitialNodeAddr(startingNodeID)
    if nodeAddr is None:
        return "ERRO! Retorno invalido do programa principal."

    #String contendo endereco do socket cliente que aguardara resposta do node final:"
    clientAddrString = "localhost,4998"

    #Composicao da Mensagem de Requisicao de Insercao:
    requestMessage = "i " + key + " " + value + " " + clientAddrString #caractere 'i' incluido no inicio da mensagem para indicar uma requisicao de insercao

    #Requisicao de insercao no Chord:
    clientSocket = socket.socket()
    clientSocket.connect(nodeAddr)
    send(requestMessage, clientSocket)
    clientSocket.close()

    #Aguarda Resposta do Chord:
    responseSocket = socket.socket()
    responseSocket.bind(('', 4998))
    responseSocket.listen()
    nodeSocket, nodeAddr = responseSocket.accept()
    responseMessage = receive(nodeSocket)
    responseSocket.close()

    return responseMessage


def busca(startingNodeID, key):
    
    #Requisita ao programa principal o endereco do node de ID startingNodeID:
    nodeAddr = getInitialNodeAddr(startingNodeID)
    if nodeAddr is None:
        return "ERRO! Retorno invalido do programa principal."

    #String contendo endereco do socket cliente que aguardara resposta do node final:"
    clientAddrString = "localhost,4998"

    #Composicao da Mensagem de Requisicao de Busca:
    requestMessage = "s " + key + " " + clientAddrString #caractere 's' incluido no inicio da mensagem para indicar uma requisicao de busca (search)

    #Requisicao de busca no Chord:
    clientSocket = socket.socket()
    clientSocket.connect(nodeAddr)
    send(requestMessage, clientSocket)
    clientSocket.close()

    #Aguarda Resposta do Chord:
    responseSocket = socket.socket()
    responseSocket.bind(('', 4998))
    responseSocket.listen()
    nodeSocket, nodeAddr = responseSocket.accept()
    responseMessage = receive(nodeSocket)
    responseSocket.close()

    return responseMessage


def getInitialNodeAddr(startingNodeID):
    mainAddr = ('', 4999) #endereco do socket do programa principal que informara ao cliente o endereco do node inicial

    #Requisicao para obter endereco do node inicial:
    clientSocket = socket.socket()
    clientSocket.connect(mainAddr)
    send(startingNodeID, clientSocket)
    addrMessage = receive(clientSocket)
    clientSocket.close()
    
    #Composicao do endereco do node inicial:
    try:
        addrMessageSplit = addrMessage.split(',')
        nodeHostName = addrMessageSplit[0]
        nodePort = int(addrMessageSplit[1])
        nodeAddr = (nodeHostName, nodePort)
    except IndexError:
        return None
    
    return nodeAddr


#Envia a mensagem (passada por parametro como string) apos adequa-la ao protocolo estabelecido:
def send(messageString, clientSocket):
    messageLength = len(messageString)
    if messageLength > 9999:
        messageString = messageString[:9999] #caso a mensagem ultrapasse o limite de 9999 caracteres, remove os caracteres extras
        messageLength = 9999
    #Header no formato "XXXX:", com os 4 Xs sendo digitos representando o tamanho da mensagem que segue os dois pontos:
    header = '0' * (4 - len(str(messageLength))) + str(messageLength) + ':'
    messageString = header + messageString #concatena o header com a mensagem a ser enviada
    message = messageString.encode('utf-8')
    return clientSocket.sendall(message)


#Recebe uma mensagem, a retornando no formato de string:
def receive(clientSocket):
    #Recebe o Header contendo o tamanho da Mensagem a ser lida:
    numberBytesRead = 0
    dataChunks = []
    while numberBytesRead < 5:
        data = clientSocket.recv(5 - numberBytesRead)
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
        data = clientSocket.recv(min(messageLength - numberBytesRead, 1024))
        if not data: return False
        dataChunks.append(data)
        numberBytesRead = numberBytesRead + len(data)
    message = str(b''.join(dataChunks), encoding = 'utf-8')

    return message


main()