import socket
import select
import sys
from operator import itemgetter
from re import findall

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

activeConnections = {} #dicionario contendo as conexoes ativas (key: sock, value: address)
inputs = [sys.stdin]   #lista contendo as entradas que serao multiplexadas pela funcao select() na main

#---CAMADA DE PROCESSAMENTO DE DADOS---:
def processData(fileName):
    fileString = accessData(fileName) #Requere os dados em formato de string da CAMADA DE ACESSO A DADOS.
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
    processedData = "Ranking de Ocorrencia de Palavras:\n"
    rank = 1
    for word, frequency in top_words:
        processedData = processedData + ("Rank %d: %s\t (%dx)\n" % (rank, word, frequency))
        rank += 1
    return processedData


#---CAMADA DE ACESSO A DADOS---:
def accessData(fileName):
    #Tenta abrir o arquivo desejado, retornando 'err' caso falhe, e retornando os dados em string contidos nele para a camada superior de processamento:
    try:
        print("Buscando arquivo: " + fileName)
        fileObject = open(fileName, 'r')
        fileString = fileObject.read()
        fileObject.close()
    except:
        print("Arquivo '" + fileName + "' não encontrado!")
        return 'err'
    print("Arquivo '" + fileName + "' encontrado!")
    return fileString


#---MAIN & FUNCOES---:

def initializeServer():
    #Cria o descritor de socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
    #Vincula o endereco e porta:
    sock.bind((HOST, PORT))
    #Se posiciona em modo de espera:
    sock.listen(5) #argumento indica quantidade de conexoes pendentes permitidas
    sock.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main
    return sock

def acceptConnection(sock):
    clientSock, addr = sock.accept()
    return clientSock, addr

def respondRequest(clientSock, addr):
    fileNameBytes = clientSock.recv(2048)
    if not fileNameBytes:
        print("Cliente " + str(addr) + " desconectado.")
        inputs.remove(clientSock) #remove o socket da lista de entradas e do dicionario de conexoes ativas
        del activeConnections[clientSock]
        clientSock.close() #fecha descritor de socket da conexao
        return #sai da funcao
    #Converte a mensagem para string e realiza a chamada da CAMADA DE PROCESSAMENTO:
    fileName = str(fileNameBytes, encoding='utf-8')
    outData = processData(fileName)
    #Converte o retorno da chamada da CAMADA DE PROCESSAMENTO para bytes e envia esses dados de volta para o Cliente:
    clientSock.send(str.encode(outData))
    print("Resposta enviada ao cliente: " + str(addr))
        

def main():

    sock = initializeServer()
    print("\nServidor inicializado! Insira \'exit\' para desligar a aplicacao.")
    inputs.append(sock)
    #Loop principal:
    while True:
        print("\nAguardando requisicao ou comando...")
        #Aceita conexao, bloqueia se nao houver pedidos de conexao, comandos no buffer sys.stdin ou requisicoes de clientes ja conectados:
        r, w, e = select.select(inputs, [], [])
        for inputToBeRead in r:
            if inputToBeRead == sock:
                newSock, address = acceptConnection(sock)
                newSock.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main
                inputs.append(newSock) #inclui o sock do novo cliente na lista de entradas a serem observadas no select
                activeConnections[newSock] = address #inclui o endereco desse cliente no dicionario para uso em logs
                print("Nova conexao com " + str(address) + " estabelecida.")
            elif inputToBeRead == sys.stdin:
                cmd = input()
                if cmd == 'exit':
                    if not activeConnections:
                        #Fecha o descritor de socket principal da aplicacao servidor e termina a aplicacao
                        print("Desligando servidor.")
                        sock.close()
                        sys.exit()
                    else:
                        print("Nao foi possivel fechar a aplicacao, aguardar termino de conexoes com clientes ativos.")
            #No caso em que a entrada lida nao seja nem o sock do servidor, nem sys.stdin: sabemos que sera uma requisicao de sock de um cliente ja conectado:
            else:
                respondRequest(inputToBeRead, activeConnections[inputToBeRead])
        #Mantem-se no loop e espera uma outra requisicao de cliente para atender ou comando do stdin...
    
main()