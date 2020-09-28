import socket
import select
import sys
import multiprocessing
from operator import itemgetter
from re import findall

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

#---CAMADA DE PROCESSAMENTO DE DADOS---:
def dataProcessingLayer(fileName):
    fileString = dataAccessLayer(fileName) #Requere os dados em formato de string da CAMADA DE ACESSO A DADOS.
    if(fileString == 'err'): return "Erro! Arquivo invalido." #Retorna uma mensagem de erro caso nao tenha sido possivel ler o arquivo. 
    
    N = 10      #numero de palavras a ranquear
    words = {}  #dicionario de palavras

    words_list = findall(r'\w+', fileString.lower()) #lista de palavras (convertidas antes para letra minuscula) do arquivo texto

    #Armazena no dicionario as palavras e seu numero de ocorrencias:
    for word in words_list: 
        words[word] = words.get(word, 0) + 1

    #Realiza o sort e armazena o resultado na lista 'top_words':
    top_words = sorted(words.items(), key=itemgetter(1), reverse=True)[:N]

    #Armazena na string 'processedData' os dados ja processados e formatados para retornar a camada superior de interface para impressao:
    processedData = "\nRanking de Ocorrencia de Palavras:\n"
    rank = 1
    for word, frequency in top_words:
        processedData = processedData + ("Rank %d: %s\t (%dx)\n" % (rank, word, frequency))
        rank += 1
    print("Dados do arquivo processados.")
    return processedData


#---CAMADA DE ACESSO A DADOS---:
def dataAccessLayer(fileName):
    #Tenta abrir o arquivo desejado, retornando 'err' caso falhe, e retornando os dados em string contidos nele para a camada superior de processamento:
    try:
        print("Buscando arquivo: " + fileName)
        fileObject = open(fileName, 'r')
        fileString = fileObject.read()
        fileObject.close()
    except:
        print("Arquivo '" + fileName + "' não encontrado.")
        return 'err'
    print("Arquivo '" + fileName + "' encontrado.")
    return fileString


#---MAIN & FUNCOES---:

class ServerCommunication:

    def __init__(self, hostIP, hostPort):
        #Cria o descritor de socket:
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
        #Vincula o endereco e porta:
        self.serverSocket.bind((hostIP, hostPort))
        #Se posiciona em modo de espera:
        self.serverSocket.listen(10)         #argumento indica quantidade de conexoes pendentes permitidas
        self.serverSocket.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main

    def acceptConnection(self):
        clientSocket, addr = self.serverSocket.accept()
        return clientSocket, addr

    def receiveFrom(self, clientSocket):
        return str(clientSocket.recv(2048), encoding = 'utf-8')

    def sendTo(self, message, clientSocket):
        clientSocket.send(str.encode(message))


class ServerInterface:

    def __init__(self, hostIP, hostPort):
        self.main(hostIP, hostPort)

    def main(self, hostIP, hostPort):
        comm = ServerCommunication(hostIP, hostPort)
        serverSocket = comm.serverSocket
        inputs = [sys.stdin, serverSocket]

        while True:
        #Aceita conexao, bloqueia se nao houver pedidos de conexao, comandos no buffer sys.stdin ou requisicoes de clientes ja conectados:
            r, w, e = select.select(inputs, [], [])
            for inputToBeRead in r:
                if inputToBeRead == serverSocket:
                    self.initiateClientSubprocess(comm)
                elif inputToBeRead == sys.stdin:
                    cmd = input()
                    if cmd == 'exit':
                        #Fecha o descritor de socket principal da aplicacao servidor e termina a aplicacao:
                        print("Desligando o servidor.")
                        serverSocket.close()
                        sys.exit()
            

    def initiateClientSubprocess(self, comm):
        clientSocket, address = comm.acceptConnection()
        print("Nova conexao com " + str(address) + " estabelecida.\n")
        #Inicia um novo processo para responder requisicoes do novo cliente com a funcao clientSubprocess, recebendo como argumentos clientSocket e address:
        clientProcess = multiprocessing.Process(target = self.clientSubprocess, args = (comm, clientSocket, address))
        clientProcess.start()


    def clientSubprocess(self, comm, clientSocket, addr):
        while True:
            request = comm.receiveFrom(clientSocket)
            if not request:
                print("Cliente " + str(addr) + " desconectado.\n")
                clientSocket.close() #fecha descritor de socket da conexao
                return #sai da funcao
            print("Requisicao do cliente " + str(addr) + " recebida.")
            #Realiza a chamada da CAMADA DE PROCESSAMENTO:
            outData = dataProcessingLayer(request)
            #Envia esses dados de volta para o Cliente:
            comm.sendTo(outData, clientSocket)
            print("Resposta enviada ao cliente.\n")
        
    
ServerInterface(HOST, PORT)