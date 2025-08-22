package com.spongebob.magic_conch_backend.service;

import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.spongebob.magic_conch_backend.DAO.WindowChat;
import com.spongebob.magic_conch_backend.DAO.windowChatRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
@Service
public class windowChatServiceImpl implements windowChatService {
    //注入data access层里面的java类
    @Autowired
    private windowChatRepository windowChatRepository;

    @Override
    public WindowChat findByName(String name) {
        //直接用父类的方法，如果不存在则抛出异常
        WindowChat windowChat = (WindowChat) windowChatRepository.findByName(name);
        if (CollectionUtils.isEmpty((Collection<?>) windowChat)) {
            throw new IllegalStateException("窗口: "+ name + "不存在");
        }
        return windowChat;
    }

    //新增业务：添加一个窗口
    @Override
    public Long createNewWindow(String name) {
        // 查找name值是否存在，存在的话就不行，因为是唯一的
        List<WindowChat> chatList = windowChatRepository.findByName(name);
        // 如果不为空，就抛出异常
        // CollectionUtils.isEmpty是 Spring Framework 提供的工具方法，用来一次性判断集合是否为 null 或 长度为 0
        if (!CollectionUtils.isEmpty(chatList)) {
            throw new IllegalStateException("窗口: "+ name + "已经存在了");
        }
        // 调用实体类对应的接口里面的save方法会自动保存，并且返回一个实体类对象
        WindowChat newChat = new WindowChat();
        newChat.setName(name);
        WindowChat newChat1 = windowChatRepository.save(newChat);
        // 返回这个窗口的id
        return newChat1.getId();
    }

    // 新增业务，页面初始化时，查询表中所有的name并返回
    @Override
    public List<WindowChat> listAll() {
        return windowChatRepository.findAll();
    }

    // 新增业务，传入窗口名字，返回窗口的text（其实这里应该按照前端的格式进行调整的，不过先不处理
    @Override
    public String getTextByName(String name) {
        List<WindowChat> listChat = windowChatRepository.findByName(name);
        if (CollectionUtils.isEmpty(listChat)) {
            throw new IllegalStateException("名字: "+ name + "不存在");
        }
        return listChat.get(0).getText();
    }

    // 新增业务，传入窗口名字和新的text，替换原来窗口的text
    public void updateText(String text, String name){
        List<WindowChat> listChat = windowChatRepository.findByName(name);
        if (CollectionUtils.isEmpty(listChat)) {
            throw new IllegalStateException("名字: "+ name + "不存在");
        }
        listChat.get(0).setText(text);
        windowChatRepository.save(listChat.get(0));
    }

    //新增业务，根据id，删除一个学生
    // 必须加这个注解，不然deleteByName方法会报错
    @Transactional
    @Override
    public void deleteWindowByName(String name) {
        // 一样先判断，如果id不存在，则抛出异常
        List<WindowChat> listChat = windowChatRepository.findByName(name);
        if (CollectionUtils.isEmpty(listChat)) {
            throw new IllegalStateException("名字: "+ name + "不存在");
        }
        windowChatRepository.deleteByName(name);
    }

//    //新增业务，根据id，更新一个学生
//    @Override
//    @Transactional   //数据操作失败后，会回滚，不会导致原来的数据丢失
//    public studentDTO updateStudentById(long id, String name, String email){
//        //如果id不存在就抛出异常
//        Student studentInDB = studentRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("id: "+id+"不存在！"));
//        //如果名字不存在，或者名字和更新后的名字不一样，才更新该学生的名字
//        if (StringUtils.hasLength(name) && !studentInDB.getName().equals(name)){
//            studentInDB.setName(name);
//        }
//        //email同理
//        if (StringUtils.hasLength(email) && !studentInDB.getEmail().equals(email)){
//            studentInDB.setEmail(email);
//        }
//        // 和新增的保存逻辑有点类似，但是这里已经是student对象了，保存的时候不需要convert，而return的时候才需要
//        Student student = studentRepository.save(studentInDB);
//        return studentConverter.convertStudent(student);
//    }
}








