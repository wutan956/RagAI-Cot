package com.spongebob.magic_conch_backend.common.enums;

/**
 * api接口返回 code和message
 *
 */
// 本枚举用于统一后端所有 API 接口的返回码（code）和返回信息（message）
// 自己理解：需要派上用场的地方：传入SUCCESS、PARAM_INVALID、ERROR这三种情况中的一种，拿到对应的code和message
public enum ResultCode {

    /* 成功 */
    SUCCESS(100, "成功"),
    /* 参数无效 */
    PARAM_INVALID(101, "参数无效"),
    /* 业务异常 */
    ERROR(999, "系统异常");

    private Integer code;

    private String message;

    /* 构造方法：创建枚举实例时给 code 和 message 赋值 */
    ResultCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
    /* 普通方法：获取当前枚举实例的 code 值 */
    public Integer code() {
        return this.code;
    }

    public String message() {
        return this.message;
    }

    /* 静态工具方法：根据枚举名字符串获取对应的 message
      例：ResultCode.getMessage("SUCCESS") -> "成功" */
    // 你把一个 字符串名字（比如 "SUCCESS"）丢进来。
    // 函数在 ResultCode 里逐个问：谁的名字跟你一样？
    // 找到了就把对应的 提示文字（"成功"）还给你；找不到就把原字符串再还给你。
    public static String getMessage(String name) {
        // ResultCode.values() 这是 Java 编译器自动给枚举生成的方法
        // 在这里相当于依次返回 SUCCESS, PARAM_INVALID, ERROR
        for (ResultCode item : ResultCode.values()) {
            if (item.name().equals(name)) {
                return item.message;
            }
        }
        return name;
    }

    // 同理，返回的是字符串名字（比如 "SUCCESS"）对应的code，如果没有则是空
    public static Integer getCode(String name) {
        for (ResultCode item : ResultCode.values()) {
            if (item.name().equals(name)) {
                return item.code;
            }
        }
        return null;
    }

    // 重写 toString：打印枚举名本身（SUCCESS / PARAM_INVALID / ERROR）
    @Override
    public String toString() {
        return this.name();
    }

}
