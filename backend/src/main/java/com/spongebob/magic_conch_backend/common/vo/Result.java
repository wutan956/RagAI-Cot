package com.spongebob.magic_conch_backend.common.vo;

// 引入自己定义的返回码枚举 & 序列化接口
import com.spongebob.magic_conch_backend.common.enums.ResultCode;
// 引入序列化接口
import java.io.Serial;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

/**
 * api接口数据返回封装
 *
 */
// 所有 REST 接口最终都会用这个 Result 对象实现
// 其实就是类似自己写的项目里的response类，但是这里给出了更全的情况，主要看里面的静态方法们
public class Result implements Serializable {

    // 序列化版本号，防止以后类结构变化导致反序列化失败
    @Serial
    private static final long serialVersionUID = -4762928619495260423L;

    //resultcode里面的那个code和msg
    private Integer code;
    private String msg;
    // 真正的业务数据
    private Object data;

    // 无参构造：留给框架（如 Jackson）反序列化用
    public Result() {
    }
    // 带 code 和 msg 的构造
    public Result(Integer code, String msg) {
        this.code = code;
        this.msg = msg;
    }

    /* ========== 各种静态工厂方法（成功） ========== */
    // 返回纯成功（data 为空）
    public static Result success() {
        Result result = new Result();  // 就是刚刚的无参构造
        result.setResultCode(ResultCode.SUCCESS); //调用下面的工具方法，设置 code=100, msg="成功"
        result.setMsg("成功");
        return result;
    }
    // 返回成功并带业务数据
    public static Result success(Object data) {
        Result result = success();
        result.setData(data);  // 在上一个方法的基础上，再把data数据也封装进result对象里面
        return result;
    }
    // 返回成功，同时自定义消息和数据
    public static Result success(Object data, String msg) {
        Result result = success();
        result.setData(data); // 在上一个方法的基础上，把data封装进去，把message重新覆盖
        result.setMsg(msg);
        return result;
    }
    /* ========== 各种静态工厂方法（失败） ========== */
    // 通用错误，默认提示“系统异常”
    public static Result error() {
        Result result = new Result();
        result.setResultCode(ResultCode.ERROR); //调用下面的工具方法，设置 code=999, msg="系统异常"
        result.setMsg("系统异常");
        return result;
    }
    // 自己指定错误消息
    public static Result error(String msg) {
        Result result = new Result();
        result.setResultCode(ResultCode.ERROR);
        result.setMsg(msg);
        return result;
    }
    // 自己指定返回码的枚举（复用 ResultCode 里定义好的提示，里面除了error就是PARAM_INVALID也就是参数无效了）
    public static Result error(ResultCode resultCode) {
        Result result = new Result();
        result.setResultCode(resultCode);
        result.setMsg("系统异常");
        return result;
    }
    // 指定返回码 + 自定义消息
    public static Result error(ResultCode resultCode, String msg) {
        Result result = new Result();
        result.setResultCode(resultCode);
        result.setMsg(msg);
        return result;
    }
    // 指定返回码 + 附带错误数据
    public static Result error(ResultCode resultCode, Object data) {
        Result result = error(resultCode);
        result.setData(data);
        return result;
    }
    // 指定返回码 + 错误数据 + 自定义消息
    public static Result error(ResultCode resultCode, Object data, String msg) {
        Result result = error(resultCode);
        result.setData(data);
        result.setMsg(msg);
        return result;
    }

    /* ========== 工具方法 ========== */
    // 快捷设置 code 和 msg 的“一键填充”
    public void setResultCode(ResultCode code) {
        this.code = code.code();
        this.msg = code.message();
    }
    public Map<String, Object> simple() {
        Map<String, Object> simple = new HashMap<String, Object>();
        this.data = simple;

        return simple;
    }


    /* ========== get方法和set方法 ========== */
    public Integer getCode() {
        return code;
    }

    public void setCode(Integer code) {
        this.code = code;
    }

    public String getMsg() {
        return msg;
    }

    public void setMsg(String msg) {
        this.msg = msg;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }


}