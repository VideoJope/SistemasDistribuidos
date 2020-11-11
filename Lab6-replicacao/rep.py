import socket
import select
import sys
import time

HOST = 'localhost'
PORT = 5000


#Copia Local da Variavel Replicada:
X = 0
#Lista com Historico de Alteracoes:
changelogX = []

#Socket passivo desta Replica:
passiveSocket = None

#ID desta Replica:
copyID = 0
#ID da Replica que Possui Copia Primaria:
primaryCopyID = 1

#Indicador de que esta Replica esta escrevendo no momento:
isWriting = False


#Inicializa o Socket Passivo da Replica:
def initializePassiveSocket(copyID):
    try:
        #Cria o descritor de socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
        #Vincula o endereco e porta:
        sock.bind((HOST, PORT + copyID)) #porta sera PORT + id da replica (este endereco sera conhecido pelas outras replicas)
        #Se posiciona em modo de espera:
        sock.listen(5)          #argumento indica quantidade de conexoes pendentes permitidas
        sock.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main
        return sock
    except:
        print("ERRO! Nao foi possivel inicializar o socket passivo desta replica. O ID inserido provavelmente ja esta em uso.")
        sys.exit()
        return


#Le do teclado o ID da Replica Atual, atualizando a variavel global copyID de acordo:
def getRepID():
    global copyID
    while True:
        try:
            copyID = int(input("Insira o ID unico desta Replica (valores inteiros de 1 a 4): "))
            if 1 <= copyID <= 4:
                return copyID
            else:
                raise ValueError
        except ValueError:
            print("ID deve ser um inteiro entre 1 e 4!")


#Trata mensagens que chegam ao Socket Passivo:
def handleIncoming():
    global passiveSocket
    global primaryCopyID
    global X


    incSocket, incAddr = passiveSocket.accept()
    incMsg = receiveFrom(incSocket)
    splitMsg = incMsg.split(',')


    #Requerimento para obter copia primaria:
    if splitMsg[0] == '$reqPrimary':

        #Se esta replica contem a copia primaria, prepara para passar o 'bastao' da escrita a quem requereu:
        if copyID == primaryCopyID:

            #Caso esta replica esteja escrevendo no momento, manda quem requereu aguardar:
            if isWriting == True:
                sendTo('WAIT', incSocket)
            #Caso contrario, passa o 'bastao':
            else:
                primaryCopyID = int(splitMsg[1]) #atualiza a variavel local com o ID que contem a copia primaria
                sendTo('OK', incSocket)          #retorna uma mensagem confirmando a passagem do 'bastao'

        #Caso contrario, retorna uma mensagem contendo o endereco da replica que contem a copia primaria: 
        else:
            response = "localhost," + str(5000 + primaryCopyID)
            sendTo(response, incSocket)


    #Mensagem de propagacao de Write:
    else:
        primaryCopyID = int(splitMsg[0])
        X = int(splitMsg[1])
        changelogX.append((primaryCopyID, X))
        sendTo('ACK', incSocket)
        print("Valor de X atualizado por uma outra replica.\n")

    return


#Trata comandos do teclado:
def handleCommand(cmd):
    global X
    global copyID
    global isWriting

    helpCommands = {'help', 'Help', '!help', '!Help'}
    exitCommands = {'exit', 'Exit', 'quit', 'Quit', 'disconnect', 'Disconnect', '!exit', '!Exit', '!quit', '!Quit', '!disconnect', '!Disconnect'}
    readCommands = {'read', 'Read', 'r', 'R', '!read', '!Read', '!r', '!R'}
    writeCommands = ['write', 'Write', 'w', 'W', '!write', '!Write', '!w', '!W']
    changelogCommands = {'log', 'Log', 'changelog', 'Changelog', '!log', '!Log', '!changelog', '!Changelog'}

    #Comando de Help:
    if cmd in helpCommands:
        print("\n=====\nComandos Disponiveis:\n")
        print("help\n  Mostra esta mensagem contendo os comandos disponiveis.\n")
        print("read\n  Le e imprime ao usuario o valor da copia da variavel X.\n")
        print("write\n  Altera o valor da variavel X e propaga o novo valor para as demais replicas quando terminar.\n")
        print("changelog\n  Mostra o historico de alteracoes feitas a variavel X.\n")
        print("exit\n  Finaliza o programa.\n=====\n")

    #Comando de Saida:
    elif cmd in exitCommands:
        print("Fechando aplicacao...")
        return False

    #Comando de Leitura:
    elif cmd in readCommands:
        print("Variavel X = " + str(X) + "\n")

    #Comando de Escrita:
    elif cmd in writeCommands:

        #Tenta obter a copia primaria. Se falhar nao tenta escrever.
        if not setAsPrimary():
            return True

        isWriting = True

        print("Insire 'commit' para terminar de escrever.")

        #Replica ainda deve estar disponivel para responder mensagens enquanto le valores para escrever em X:
        inputs = [sys.stdin, passiveSocket]
        changeMade = False

        print("Novo valor de X:", end = " ", flush = True)
        while True:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                #Le do teclado um novo valor para X ou o comando de 'commit':
                if inputToBeRead == sys.stdin:
                    cmd = input()
                    if cmd != 'commit':
                        #Atualiza X com o valor inserido:
                        try:
                            X = int(cmd)
                            changelogX.append((copyID, X))
                            changeMade = True
                        except ValueError:
                            print("Valor deve ser um inteiro!")
                        print("Novo valor de X:", end = " ", flush = True)
                    else:
                        #Propaga o valor final de X caso tenha sido feita alguma alteracao a ele:
                        if changeMade == False:
                            print("Nenhuma mudanca foi realizada na variavel!\n")
                            isWriting = False
                            return True
                        propagateWrite()
                        isWriting = False
                        print("Valor atualizado e propagado para demais replicas!\n")
                        return True
                #Caso receber alguma mensagem no socket passivo durante o processo de escrita, responde a ela:
                elif inputToBeRead == passiveSocket:
                    handleIncoming()

    #Comando de Log:
    elif cmd in changelogCommands:
        print("Historico de Atualizacoes (id, valor):")
        print(str(changelogX) + "\n")

    #Comando Invalido:
    else:
        print("Comando invalido! Digite \'help\' para uma lista de comandos disponiveis.\n")

    return True


#Tenta tornar a replica atual a detentora da Copia Primaria. Retorna True se conseguir e False se falhar:
def setAsPrimary():
    global primaryCopyID

    if copyID != primaryCopyID:
        primaryAddr = (HOST, 5000 + primaryCopyID)
        while True:
            try:
                response = sendMessageAndWaitResponse("$reqPrimary," + str(copyID), primaryAddr)
            except ConnectionRefusedError:
                print("Nao foi possivel contatar a replica que contem a Copia Primaria.\nA escrita sera permitida e ao ser propagado o resultado, esta replica se tornara sua detentora.")
                response = 'OK'

            if response == 'OK':
                primaryCopyID = copyID
                print("\nCopia Primaria obtida!")
                return True
            elif response == 'WAIT':
                print("Replica detentora da Copia Primaria ocupada escrevendo. Tente novamente mais tarde!\n")
                return False
            else:
                primaryAddr = (response.split(',')[0], int(response.split(',')[1]))

        print("ERRO! Nao foi possivel obter a Copia Primaria, tente novamente.")
        return False

    return True


#Envia as demais replicas o ID que realizou a mudanca e o novo valor de X:
def propagateWrite():
    global isWriting
    for id in range(1, 5):
        if id != copyID:
            try:
                ack = sendMessageAndWaitResponse(str(copyID) + ',' + str(X), (HOST, 5000 + id))
            except ConnectionRefusedError:
                pass
    isWriting = False
    return




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

#Envia a mensagem (passada por parametro como string) ao socket alvo apos adequa-la ao protocolo estabelecido:
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


#Cria um socket ativo para envio da mensagem 'message' direcionado ao endereco 'address' de um Socket Passivo e aguarda a mensagem de resposta:
def sendMessageAndWaitResponse(message, address):

    outgoingSocket = socket.socket()
    outgoingSocket.connect(address)
    sendTo(message, outgoingSocket)
    #print("passei do sendTo") TODO del
    returnMsg = receiveFrom(outgoingSocket)
    #print("passei do receiveFrom") TODO del
    outgoingSocket.close()

    return returnMsg




#Main:
def main():
    global passiveSocket

    copyID = getRepID()
    passiveSocket = initializePassiveSocket(copyID)

    inputs = [sys.stdin, passiveSocket]

    print("\nPrograma inicializado! Insira o comando \'help\' para uma lista de comandos disponiveis.\n")

    while True:
        r, w, e = select.select(inputs, [], [])
        for inputToBeRead in r:
            if inputToBeRead == passiveSocket:
                handleIncoming()
            elif inputToBeRead == sys.stdin:
                cmd = input()
                if not handleCommand(cmd):
                    passiveSocket.close()
                    return
    return


main()