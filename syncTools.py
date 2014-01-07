#-*- coding: utf-8 -*-
#
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
from pysvn import opt_revision_kind
from pysvn import wc_status_kind
import chardet
import cookielib
import datetime
import os
import pysvn
import re
import sys
import traceback
import urllib
import urllib2
import codecs

reload(sys)
sys.setdefaultencoding('utf-8')


class ToolException(Exception):
    pass

LOGIN_POSTFIX = '/admin/admin/login'
IMPORT_POSTFIX = '/admin/staticInfo/import'
GENERATE_POSTFIX = '/admin/configxml/newXmlUpload'
EXPORT_POSTFIX = '/admin/staticInfo/export'


def generateConfigFile():
    print u"---生成用户配置文件"
    while True:
        host = raw_input(
            u"   目标平台地址(eg.http://admintools.wsg2.com):".encode("gbk"))
        username = raw_input(u"   用户名:".encode("gbk"))
        password = raw_input(u"   密码:".encode("gbk"))
        username = username.decode('gbk').encode("utf-8")
        if login(host, username, password):
            break
        pass
    while True:
        generateXML = raw_input(u"   是否自动生成config(Y/N):".encode("gbk"))
        if generateXML == "Y" or generateXML == "N":
            break
        else:
            print u"   请输入 Y(Yes)/N(No)"
        pass

    svnDir = os.path.abspath('..')
    svnDir = svnDir.decode("gbk").encode("utf-8")

    content = "\n".join([username, password, host, svnDir, generateXML])
    # configContent
    configf = codecs.open('config', 'w', 'utf-8')
    configf.write(content)
    configf.close()
    print u"   保存配置成功"


def loadConfig():
    if os.path.exists('config'):
        config = open('config')
    else:
        return False
    configContent = config.read()
    config.close()
    # encoding = chardet.detect(configContent)["encoding"]
    # configContent = configContent.decode(encoding).encode("utf-8")
    global username, password, host, svnDir, generateXML, bcomparePath
    lines = configContent.splitlines()
    # print len(lines)
    if len(lines)==5:
        username, password, host, svnDir, generateXML = lines
    else:
        username, password, host, svnDir, generateXML, bcomparePath = lines
    return True


def login(host, username, password):
    opener = register_openers()
    data = {"username": username, "passwd": password,
            "platform": "weiyouxi", "dosubmit": " 登 录 "}
    post_data = urllib.urlencode(data)
    cj = cookielib.CookieJar()
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))
    req = urllib2.Request(host + LOGIN_POSTFIX, post_data)
    try:
        content = urllib2.urlopen(req).read()
        pass
    except Exception, e:
        print u"\n---登录后台错误,请检查登录地址或网络连接"
        return False
    if re.search(r'登录后台成功!', content):
        print u"\n---登录后台成功!"
        return True
    else:
        print u"\n---登录后台失败!"
        return False


def getUploadFileList(svnDir):
    '''get modified file list'''
    print u"---获取版本差异"
    client = pysvn.Client()
    client.update(svnDir)
    for status in client.status(svnDir):
        if status['text_status'] == wc_status_kind.conflicted:
            raise ToolException(u"文件冲突 %s" % status["path"])
        elif status['text_status'] == wc_status_kind.modified:
            raise ToolException(u"文件修改未提交 %s" % status["path"])
        elif status['text_status'] == wc_status_kind.unversioned:
            raise ToolException(u"新文件未提交 %s" % status["path"])
        elif status['text_status'] == wc_status_kind.deleted:
            raise ToolException(u"删除文件未提交 %s" % status["path"])
    currentRevision = client.info(svnDir).commit_revision.number
    revisionFile = open(
        os.path.join(svnDir.decode("utf-8"), 'tools', 'log.txt'), 'r')

    lastSyncRevision = revisionFile.read()
    revisionFile.close()

    if int(lastSyncRevision) >= int(currentRevision):
        raise ToolException(u'服务器版本号(%s)大于或等于svn版本号(%s)' %
                            (lastSyncRevision, currentRevision))
    else:
        print u"   版本差异(%s-%s):" % (lastSyncRevision, currentRevision)

    try:
        diffList = \
            client.diff_summarize(svnDir,
                                  revision1=pysvn.Revision(
                                  opt_revision_kind.number, lastSyncRevision),
                                  url_or_path2=svnDir,
                                  revision2=pysvn.Revision(
                                  opt_revision_kind.number, currentRevision),
                                  recurse=True)
        pass
    except Exception, e:
        raise ToolException(
            u"所标记的版本在目标svn库中不存在，请在tools文件夹下修改log.txt指定一个svn库中存在的版本")
    changedFiles = []

    for changed in diffList:
        if pysvn.diff_summarize_kind.modified == changed['summarize_kind'] or pysvn.diff_summarize_kind.added == changed['summarize_kind']:
            if os.path.splitext(changed['path'])[1] == '.xls':
                changedFiles.append(os.path.join(svnDir, changed['path']))
                try:
                    print u"    %s %s" % (changed['path'], str(changed['summarize_kind']))
                except Exception, e:
                    print u"    *文件名读取错误"
                    pass
    return (changedFiles, lastSyncRevision, currentRevision)
    pass


def upload(host, excfiles, generateXML='Y'):
    '''upload file'''
    print u"\n---上传文件"
    for item in excfiles:
        try:
            print u"    %s" % os.path.basename(item)
        except Exception, e:
            print u"    *文件名读取错误"
        pass
        tableName = os.path.basename(item).split('.')[0]
        matchResult = re.search(r'(?<=\()\w*(?=\))', tableName)
        if matchResult:
            tableName = matchResult.group(0)
        else:
            raise ToolException(
                "%s 文件名错误(eg. 游戏配置表(info_game_setting)" % os.path.basename(item))
        datagen, headers = multipart_encode(
            {"file": open(item, "rb"), 'table': tableName})
        req = urllib2.Request(host + IMPORT_POSTFIX, datagen, headers)
        content = urllib2.urlopen(req).read()
        if re.search(r'导入成功', content):
            print u"    -上传成功!"
        else:
            raise ToolException(u"上传失败!")
    print u"\n---上传文件完毕"
    if generateXML == "Y":
        req = urllib2.Request(host + GENERATE_POSTFIX)
        content = urllib2.urlopen(req).read()
        if re.search(r'已生成', content):
            print u"\n---配置文件已生成"
        else:
            print u"\n---配置文件生成失败"
    else:
        print u"\n---不需要生成配置文件"

    pass


def tagRevision(svnDir, revisionNumber):
    print u'\n---更新版本号 ' + str(revisionNumber + 1)
    output = open(
        os.path.join(svnDir.decode("utf-8"), 'tools', 'log.txt'), 'w')
    output.write(str(revisionNumber + 1))
    output.close()
    client = pysvn.Client()
    client.checkin(svnDir, '同步表')
    pass


def downloadTables(host, dirPath):
    print u"\n---下载所有配表"
    fileNames = open(
        os.path.join(dirPath.decode("utf-8"), 'tools', 'content.txt')).readlines()
    for fileName in fileNames:
        fileName = fileName.strip("\n")
        tableName = getTableName(fileName)
        print u"   " + tableName
        downloadTable(host,tableName,os.path.join(dirPath, fileName.decode("utf-8") + '.xls'))
    print u"---下载完毕"
    pass

def getTableName(fileName):
    matchResult = re.search(r'(?<=\()\w*(?=\))', fileName)
    if matchResult:
        tableName = matchResult.group(0)
    else:
        raise ToolException(
            "%s 文件名错误(eg. 游戏配置表(info_game_setting)" % os.path.basename(item))
    return tableName

def downloadTable(host,tableName,savePath):
    params = {'table': tableName}
    params = urllib.urlencode(params)
    ret = urllib2.urlopen("%s?%s" % (host + EXPORT_POSTFIX, params))
    with open(savePath, 'wb') as code:
        code.write(ret.read())
    pass
def main():
    try:
        if not loadConfig():
            generateConfigFile()
            loadConfig()
            doDownloading = raw_input(u"   是否下载所有配置表(Y/N):".encode("gbk"))
            if doDownloading == 'Y':
                downloadTables(host, svnDir)
                return
            pass
        filelist, lastSyncRevision, currentRevision = getUploadFileList(
            svnDir)

        if int(lastSyncRevision) >= int(currentRevision) or len(filelist) == 0:
            raise ToolException(u"没有变更文件")
        else:
            if login(host, username, password):
                upload(host, filelist, generateXML)
                tagRevision(svnDir, currentRevision)
                pass
    except Exception, e:
        if isinstance(e, ToolException):
            msg = e.message
        else:
            msg = str(e)
            msg = msg + "\n\n" + traceback.format_exc()
        print '''
    ******************************
    ERROR! %s
    ******************************
        ''' % msg
        pass
    pass


def getEncoding(stringToDetect):
    return chardet.detect(stringToDetect)["encoding"]
    pass
if __name__ == '__main__':
    print "======================================"
    main()
    print "======================================"
    os.system("pause")
    # loadConfig()
    # login(host, username, password)
    # downloadTables(host, svnDir)
