package com.spongebob.magic_conch_backend.service;
import com.spongebob.magic_conch_backend.DAO.WindowChat;
import java.util.List;

public interface windowChatService {
    WindowChat findByName(String name);

    Long createNewWindow(String name);

    List<WindowChat> listAll();

    // 传入名字，返回对应窗口的text
    String getTextByName(String name);

    // 传入名字和text，更新对应窗口的text
    void updateText(String text, String name);

    // 新增根据id，删除学生的方法
    void deleteWindowByName(String name);

}


