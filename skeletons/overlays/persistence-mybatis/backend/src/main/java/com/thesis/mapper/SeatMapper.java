package com.thesis.mapper;

import org.apache.ibatis.annotations.*;

import java.sql.Timestamp;
import java.util.List;
import java.util.Map;

@Mapper
public interface SeatMapper {
    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='cinema_seat'")
    Integer countTable();

    @Select("SELECT id, title, price_yuan AS author, hall_note AS isbn, category_id AS categoryId, stock, status, "
            + "cover_url AS coverUrl, seat_rows AS seatRows, seat_cols AS seatCols, "
            + "DATE_FORMAT(start_at, '%Y-%m-%d %H:%i:%s') AS startAt "
            + "FROM cinema_show WHERE status='available' AND stock>0 "
            + "AND (start_at IS NULL OR start_at > NOW()) ORDER BY id DESC")
    List<Map<String, Object>> listOpenShows();

    @Select("SELECT id, title, price_yuan AS author, hall_note AS isbn, category_id AS categoryId, stock, status, "
            + "cover_url AS coverUrl, seat_rows AS seatRows, seat_cols AS seatCols, "
            + "DATE_FORMAT(start_at, '%Y-%m-%d %H:%i:%s') AS startAt "
            + "FROM cinema_show WHERE id=#{id}")
    Map<String, Object> getShow(long id);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId}")
    Integer countSeats(long showId);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId} AND status IN ('sold','held')")
    Integer countBusy(long showId);

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='cinema_seat' AND column_name='hold_until'")
    Integer countHoldColumn();

    @Select("SELECT COUNT(*) FROM information_schema.columns "
            + "WHERE table_schema=DATABASE() AND table_name='cinema_seat' AND column_name='seat_attr'")
    Integer countSeatAttrColumn();

    @Select("SELECT name FROM category WHERE id=#{id}")
    String getCategoryName(long id);

    @Insert("INSERT IGNORE INTO cinema_seat (show_id, seat_code, status) VALUES (#{showId}, #{seatCode}, 'free')")
    int insertSeat(@Param("showId") long showId, @Param("seatCode") String seatCode);

    @Delete({
        "<script>",
        "DELETE FROM cinema_seat WHERE show_id=#{showId} AND status='free'",
        "<if test='codes != null and codes.size() &gt; 0'>",
        " AND seat_code NOT IN ",
        "<foreach collection='codes' item='c' open='(' separator=',' close=')'>#{c}</foreach>",
        "</if>",
        "</script>"
    })
    int deleteFreeOutside(@Param("showId") long showId, @Param("codes") List<String> codes);

    @Update("UPDATE cinema_show SET stock=#{stock} WHERE id=#{showId}")
    int updateShowStock(@Param("showId") long showId, @Param("stock") int stock);

    @Update("UPDATE cinema_show SET status='unavailable' "
            + "WHERE status IN ('available','sold_out') AND start_at IS NOT NULL AND start_at <= NOW()")
    int expirePastShows();

    @Update("UPDATE cinema_show SET status='sold_out' WHERE stock<=0 "
            + "AND status IN ('available','unavailable') AND (start_at IS NULL OR start_at > NOW())")
    int markSoldOut();

    @Update("UPDATE cinema_show SET status='available' WHERE stock>0 AND status='sold_out' "
            + "AND (start_at IS NULL OR start_at > NOW())")
    int reopenSoldOut();

    @Update("UPDATE cinema_show SET status='sold_out' WHERE id=#{showId} AND stock<=0 "
            + "AND status IN ('available','unavailable') AND (start_at IS NULL OR start_at > NOW())")
    int markSoldOutOne(@Param("showId") long showId);

    @Update("UPDATE cinema_show SET status='available' WHERE id=#{showId} AND stock>0 AND status='sold_out' "
            + "AND (start_at IS NULL OR start_at > NOW())")
    int reopenSoldOutOne(@Param("showId") long showId);

    @Select("SELECT id, show_id AS showId, seat_code AS seatCode, status, username, order_id AS orderId, "
            + "sold_at AS soldAt, hold_until AS holdUntil, held_by AS heldBy, seat_attr AS seatAttr "
            + "FROM cinema_seat WHERE show_id=#{showId} ORDER BY seat_code")
    List<Map<String, Object>> listSeats(long showId);

    @Update("UPDATE cinema_seat SET seat_attr=#{attr} WHERE show_id=#{showId} AND seat_code=#{seatCode}")
    int updateSeatAttr(
            @Param("showId") long showId,
            @Param("seatCode") String seatCode,
            @Param("attr") String attr);

    @Select("SELECT COUNT(*) FROM cinema_seat WHERE show_id=#{showId} AND seat_code=#{seatCode} "
            + "AND (status='free' OR (status='held' AND username=#{username}))")
    Integer countClaimableSeat(
            @Param("showId") long showId,
            @Param("seatCode") String seatCode,
            @Param("username") String username);

    @Update("UPDATE cinema_seat SET status='sold', username=#{username}, order_id=#{orderId}, sold_at=#{soldAt}, "
            + "hold_until=NULL, held_by=NULL "
            + "WHERE show_id=#{showId} AND seat_code=#{seatCode} "
            + "AND (status='free' OR (status='held' AND username=#{username}))")
    int sellSeat(
            @Param("showId") long showId,
            @Param("seatCode") String seatCode,
            @Param("username") String username,
            @Param("orderId") long orderId,
            @Param("soldAt") Timestamp soldAt);

    @Update("UPDATE cinema_seat SET status='held', username=#{username}, held_by=#{username}, hold_until=#{until} "
            + "WHERE show_id=#{showId} AND seat_code=#{seatCode} "
            + "AND (status='free' OR (status='held' AND username=#{username}))")
    int holdSeat(
            @Param("showId") long showId,
            @Param("seatCode") String seatCode,
            @Param("username") String username,
            @Param("until") Timestamp until);

    @Update("UPDATE cinema_seat SET status='free', username=NULL, held_by=NULL, hold_until=NULL "
            + "WHERE status='held' AND (hold_until IS NULL OR hold_until<=NOW())")
    int releaseExpiredHolds();

    @Update("UPDATE cinema_seat SET status='free', username=NULL, held_by=NULL, hold_until=NULL "
            + "WHERE show_id=#{showId} AND status='held' AND username=#{username}")
    int releaseMineHolds(@Param("showId") long showId, @Param("username") String username);

    @Update({
        "<script>",
        "UPDATE cinema_seat SET status='free', username=NULL, held_by=NULL, hold_until=NULL ",
        "WHERE show_id=#{showId} AND status='held' AND username=#{username}",
        "<if test='codes != null and codes.size() &gt; 0'>",
        " AND seat_code NOT IN ",
        "<foreach collection='codes' item='c' open='(' separator=',' close=')'>#{c}</foreach>",
        "</if>",
        "</script>"
    })
    int releaseMineHoldsExcept(
            @Param("showId") long showId,
            @Param("username") String username,
            @Param("codes") List<String> codes);

    @Update("UPDATE cinema_seat SET status='free', username=NULL, order_id=NULL, sold_at=NULL, "
            + "hold_until=NULL, held_by=NULL WHERE order_id=#{orderId} AND status='sold'")
    int releaseByOrder(long orderId);

    @Select("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='cinema_snack'")
    Integer countSnackTable();

    @Select("SELECT id, title, price_yuan AS priceYuan, stock, status FROM cinema_snack "
            + "WHERE status='on' AND stock>0 ORDER BY id")
    List<Map<String, Object>> listOpenSnacks();

    @Select("SELECT id, title, price_yuan AS priceYuan, stock, status FROM cinema_snack ORDER BY id")
    List<Map<String, Object>> listAllSnacks();

    @Select("SELECT id, title, price_yuan AS priceYuan, stock, status FROM cinema_snack WHERE id=#{id}")
    Map<String, Object> getSnack(long id);

    @Update("UPDATE cinema_snack SET title=#{title}, price_yuan=#{priceYuan}, stock=#{stock}, status=#{status} WHERE id=#{id}")
    int updateSnack(
            @Param("id") long id,
            @Param("title") String title,
            @Param("priceYuan") double priceYuan,
            @Param("stock") int stock,
            @Param("status") String status);

    @Insert("INSERT INTO cinema_snack (title, price_yuan, stock, status) VALUES (#{title}, #{priceYuan}, #{stock}, #{status})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insertSnack(Map<String, Object> row);

    @Update("UPDATE cinema_snack SET stock=stock+#{delta} WHERE id=#{id} AND stock>=#{need}")
    int adjustSnackStockDown(
            @Param("id") long id, @Param("delta") int delta, @Param("need") int need);

    @Update("UPDATE cinema_snack SET stock=stock+#{delta} WHERE id=#{id}")
    int adjustSnackStockUp(@Param("id") long id, @Param("delta") int delta);
}
