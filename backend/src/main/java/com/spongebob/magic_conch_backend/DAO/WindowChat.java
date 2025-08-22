package com.spongebob.magic_conch_backend.DAO;
//import jakarta.persistence.*;  //因为版本较高，所以换这个版本
import jakarta.persistence.*;

/**
 * 聊天窗口实体，对应 MySQL 表 window_chat
 */
@Entity                 // 1. 声明为 JPA 实体
@Table(name = "window_chat")
public class WindowChat {

    @Id     // 2. 主键
    @Column(name = "id")
    @GeneratedValue(strategy = GenerationType.IDENTITY)     // 3. 自增
    private long id;

    @Column(nullable = false, name = "name")                               // 4. name 不能为空
    private String name;
    @Column(columnDefinition = "longtext", name = "text")                  // 5. 长文本字段
    private String text;

    /* ---------- Getter & Setter ---------- */
    public long getId() {
        return id;
    }
    public void setId(Integer id) {
        this.id = id;
    }
    public String getName() {
        return name;
    }
    public void setName(String name) {
        this.name = name;
    }
    public String getText() {
        return text;
    }
    public void setText(String text) {
        this.text = text;
    }
    public String toString(){
        return "id"+id+"name"+name+"text"+text;
    }
}