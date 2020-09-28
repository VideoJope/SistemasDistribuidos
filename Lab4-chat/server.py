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

def initializeServer():
    #Cria o descritor de socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP
    #Vincula o endereco e porta:
    sock.bind((HOST, PORT))
    #Se posiciona em modo de espera:
    sock.listen(5)          #argumento indica quantidade de conexoes pendentes permitidas
    sock.setblocking(False) #torna o socket nao bloqueante, deixando o bloqueio a cargo da funcao select() na main
    return sock

def acceptConnection(sock):
    clientSock, addr = sock.accept()
    return clientSock, addr

def respondRequests(clientSock, addr):
    #clientSock.send(str.encode("TESTE")) #DELETA DEPOIS
    while True:
        fileNameBytes = clientSock.recv(2048)
        if not fileNameBytes:
            print("Cliente " + str(addr) + " desconectado.\n")
            clientSock.close() #fecha descritor de socket da conexao
            return #sai da funcao
        print("Requisicao do cliente " + str(addr) + " recebida.")
        #Converte a mensagem para string e realiza a chamada da CAMADA DE PROCESSAMENTO:
        fileName = str(fileNameBytes, encoding='utf-8')
        outData = dataProcessingLayer(fileName)
        #Converte o retorno da chamada da CAMADA DE PROCESSAMENTO para bytes e envia esses dados de volta para o Cliente:
        clientSock.send(str.encode(outData))
        print("Resposta enviada ao cliente.\n")
        

def main():

    sock = initializeServer()
    print("\nServidor inicializado! Insira o comando \'exit\' para nao aceitar novas conexoes e terminar a aplicacao.")
    print("Aguardando conexoes...\n")
    inputs = [sys.stdin, sock] #lista das entradas que serao multiplexadas pela funcao select()
    clientProcessesList = [] #lista dos processos criados ao longo da execucao para atender clientes

    #Loop principal:
    while True:
        #Aceita conexao, bloqueia se nao houver pedidos de conexao, comandos no buffer sys.stdin ou requisicoes de clientes ja conectados:
        r, w, e = select.select(inputs, [], [])
        for inputToBeRead in r:
            if inputToBeRead == sock:
                clientSock, address = acceptConnection(sock)
                print("Nova conexao com " + str(address) + " estabelecida.\n")
                #Inicia um novo processo para responder requisicoes do novo cliente com a funcao respondRequests, recebendo como argumentos clientSock e address:
                clientProcess = multiprocessing.Process(target = respondRequests, args = (clientSock, address))
                clientProcess.start()
                clientProcessesList.append(clientProcess)
            elif inputToBeRead == sys.stdin:
                cmd = input()
                if cmd == 'exit':
                    print("O servidor nao ira responder a novos clientes e desligara automaticamente apos atender clientes ativos em sessao...\n")
                    for c in clientProcessesList:
                        c.join()
                    #Fecha o descritor de socket principal da aplicacao servidor e termina a aplicacao:
                    print("Nenhum cliente ativo pendente.\nDesligando o servidor.")
                    sock.close()
                    sys.exit()
        #Mantem-se no loop e espera uma outra requisicao de cliente para atender ou comando do console para tratar...
    
main()