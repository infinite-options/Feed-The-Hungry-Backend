#To run program:  python3 fth_api.py prashant

#README:  if conn error make sure password is set properly in RDS PASSWORD section

#README:  Debug Mode may need to be set to Fales when deploying live (although it seems to be working through Zappa)

#README:  if there are errors, make sure you have all requirements are loaded
#pip3 install flask
#pip3 install flask_restful
#pip3 install flask_mail
#pip3 install flask_cors
#pip3 install Werkzeug
#pip3 install pymysql
#pip3 install python-dateutil


from flask import Flask, request, render_template, url_for, redirect
from flask_restful import Resource, Api
from flask_mail import Mail, Message  # used for email
# used for serializer email and error handling
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil

import string
import decimal
import sys
import json
import pymysql
import requests

RDS_HOST = 'pm-mysqldb.cxjnrciilyjq.us-west-1.rds.amazonaws.com'
#RDS_HOST = 'localhost'
RDS_PORT = 3306
#RDS_USER = 'root'
RDS_USER = 'admin'
RDS_DB = 'feed_the_hungry'

app = Flask(__name__)

# Allow cross-origin resource sharing
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# Set this to false when deploying to live application
app.config['DEBUG'] = True

# Adding for email testing
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'fthtesting@gmail.com'
app.config['MAIL_PASSWORD'] = 'infiniteoptions0422'
app.config['MAIL_DEFAULT_SENDER'] = 'fthtesting@gmail.com'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
# app.config['MAIL_DEBUG'] = True
# app.config['MAIL_SUPPRESS_SEND'] = False
# app.config['TESTING'] = False

mail = Mail(app)

# API
api = Api(app)

# Get RDS password from command line argument
def RdsPw():
    if len(sys.argv) == 2:
        return str(sys.argv[1])
    return ""

# RDS PASSWORD
# When deploying to Zappa, set RDS_PW equal to the password as a string
# When pushing to GitHub, set RDS_PW equal to RdsPw()
RDS_PW = 'prashant'
# RDS_PW = RdsPw()


getToday = lambda: datetime.strftime(date.today(), "%Y-%m-%d")
getNow = lambda: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")

# Connect to RDS
def getRdsConn(RDS_PW):
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS...")
    try:
        conn = pymysql.connect(RDS_HOST,
                               user=RDS_USER,
                               port=RDS_PORT,
                               passwd=RDS_PW,
                               db=RDS_DB)
        cur = conn.cursor()
        print("Successfully connected to RDS.")
        return [conn, cur]
    except:
        print("Could not connect to RDS.")
        raise Exception("RDS Connection failed.")

# Connect to MySQL database (API v2)
def connect():
    global RDS_PW
    global RDS_HOST
    global RDS_PORT
    global RDS_USER
    global RDS_DB

    print("Trying to connect to RDS (API v2)...")
    try:
        conn = pymysql.connect( RDS_HOST,
                                user=RDS_USER,
                                port=RDS_PORT,
                                passwd=RDS_PW,
                                db=RDS_DB,
                                cursorclass=pymysql.cursors.DictCursor)
        print("Successfully connected to RDS. (API v2)")
        return conn
    except:
        print("Could not connect to RDS. (API v2)")
        raise Exception("RDS Connection failed. (API v2)")

# Disconnect from MySQL database (API v2)
def disconnect(conn):
    try:
        conn.close()
        print("Successfully disconnected from MySQL database. (API v2)")
    except:
        print("Could not properly disconnect from MySQL database. (API v2)")
        raise Exception("Failure disconnecting from MySQL database. (API v2)")

# Serialize JSON
def serializeResponse(response):
    try:
        for row in response:
            for key in row:
                if type(row[key]) is Decimal:
                    row[key] = float(row[key])
                elif type(row[key]) is date or type(row[key]) is datetime:
                    row[key] = row[key].strftime("%Y-%m-%d")
        return response
    except:
        raise Exception("Bad query JSON")

# Execute an SQL command (API v2)
# Set cmd parameter to 'get' or 'post'
# Set conn parameter to connection object
# OPTIONAL: Set skipSerialization to True to skip default JSON response serialization
def execute(sql, cmd, conn, skipSerialization = False):
    response = {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cmd is 'get':
                result = cur.fetchall()
                response['message'] = 'Successfully executed SQL query.'
                # Return status code of 280 for successful GET request
                response['code'] = 280
                if not skipSerialization:
                    result = serializeResponse(result)
                response['result'] = result
            elif cmd in 'post':
                conn.commit()
                response['message'] = 'Successfully committed SQL command.'
                # Return status code of 281 for successful POST request
                response['code'] = 281
            else:
                response['message'] = 'Request failed. Unknown or ambiguous instruction given for MySQL command.'
                # Return status code of 480 for unknown HTTP method
                response['code'] = 480
    except:
        response['message'] = 'Request failed, could not execute MySQL command.'
        # Return status code of 490 for unsuccessful HTTP request
        response['code'] = 490
    finally:
        response['sql'] = sql
        return response

# Close RDS connection
def closeRdsConn(cur, conn):
    try:
        cur.close()
        conn.close()
        print("Successfully closed RDS connection.")
    except:
        print("Could not close RDS connection.")

# Runs a select query with the SQL query string and pymysql cursor as arguments
# Returns a list of Python tuples
def runSelectQuery(query, cur):
    try:
        cur.execute(query)
        queriedData = cur.fetchall()
        return queriedData
    except:
        raise Exception("Could not run select query and/or return data")


# -- Queries start here -------------------------------------------------------------------------------

# QUERY 1
# DONATION INFORMATION: FoodBankID, FoodbankName, Donor Name, Total Donations, Donation Date
class DonorValuation(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            print("P")
            items = execute("""
                        SELECT 
                                d.donor_id,
                                donor_first_name,
                                donor_last_name,
                                donation_date,
                                donation_foodbank_id,
                                fb_name,
                                sum(total) totalDonation,
                                sum(food_count) total_qty
                        FROM (
                            SELECT donation_foodbank_id,
                                    donor_id,
                                    donation_date,
                                    foodID,
                                    count(foodID) AS food_count,
                                    round(count(foodID) * fl_value_in_dollars, 2) total
                            FROM (
                                    SELECT donation_foodbank_id,
                                        donor_id,
                                        donation_date,
                                        trim('"' FROM cast(json_extract(donation_food_list, val) as CHAR)) AS foodID
                                    FROM donations
                                    JOIN numbers ON JSON_LENGTH(donation_food_list) > n - 1) AS t
                            JOIN food_list ON food_id = foodID
                            GROUP BY donation_foodbank_id, donor_id, foodID)AS temp
                        LEFT JOIN donor d ON d.donor_id = temp.donor_id
                        JOIN foodbanks ON donation_foodbank_id = foodbank_id
                        GROUP BY foodbank_id, d.donor_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 2
# DONATED ITEMS BY FOODBANK
class ItemDonations(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                        SELECT foodbank_id
                            , fb_name
                            , foodID
                            , fl_name
                            , TotalDonation AS Donation_Qty
                            , round(TotalDonation * fl_value_in_dollars, 2) totalDonation
                        FROM (
                                SELECT donation_foodbank_id
                                    , trim('"' FROM cast(json_extract(donation_food_list, val) AS CHAR)) AS foodID
                                    , COUNT(trim('"' FROM cast(json_extract(donation_food_list, val) AS CHAR))) AS TotalDonation
                                FROM donations
                                JOIN numbers ON JSON_LENGTH(donation_food_list) > n - 1
                                GROUP BY donation_foodbank_id, foodID) AS temp
                        JOIN food_list ON food_id = foodID
                        JOIN foodbanks ON donation_foodbank_id = foodbank_id
                        ORDER BY TotalDonation DESC;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# QUERY 3
# TYPES OF FOOD DONATED
class TypesOfFood(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT  foodbank_id
                        , fb_name
                        , fl_type
                        , count(fl_type) AS Donation_Qty
                        , round(count(fl_type) * fl_value_in_dollars, 2) AS totalDonation
                FROM (
                    SELECT donation_foodbank_id
                        , trim('"' FROM cast(json_extract(donation_food_list, val) AS CHAR)) AS foodID
                    FROM donations
                    JOIN numbers on JSON_LENGTH(donation_food_list) > n - 1)
                    AS temp
                JOIN food_list ON foodID = food_id
                JOIN foodbanks ON donation_foodbank_id = foodbank_id
                GROUP BY foodbank_id, fl_type;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 4
# DONATIONS BY DATE
class DonationbyDate(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
               SELECT  foodbank_id
                        , fb_name
                        , donations_date
                        , foodID
                        , quantity
                        , fl_name
                        , round(quantity * fl_value_in_dollars, 2) AS totalDonation
                FROM (
                    SELECT donation_foodbank_id
                        , date(STR_TO_DATE(donation_date, '%c-%e-%Y %H:%i:%s')) AS donations_date
                        , trim('"' FROM cast(json_extract(donation_food_list, val) as CHAR)) AS foodID
                        , COUNT(trim('"' FROM cast(json_extract(donation_food_list, val) as CHAR))) AS quantity
                    FROM donations
                    JOIN numbers ON JSON_LENGTH(donation_food_list) > n - 1
                    GROUP BY donations_date, foodID, donation_foodbank_id) AS temp
                JOIN food_list ON foodID = food_id
                JOIN foodbanks ON foodbank_id = donation_foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class DonationbyFood(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
               SELECT  foodbank_id
                        , fb_name
                        , donor_id
                        , foodID
                        , fl_name
                        , quantity as quantityDonated
                        , round(quantity * fl_value_in_dollars, 2) AS valueDonated
                        , donations_date
                FROM (
                    SELECT donation_foodbank_id
                        , trim('"' FROM cast(json_extract(donation_food_list, val) as CHAR)) AS foodID
                        , COUNT(trim('"' FROM cast(json_extract(donation_food_list, val) as CHAR))) AS quantity
                        , donor_id
                        , date(STR_TO_DATE(donation_date, '%c-%e-%Y %H:%i:%s')) AS donations_date

                    FROM donations
                    JOIN numbers ON JSON_LENGTH(donation_food_list) > n - 1
                    GROUP BY donor_id, foodID, donation_foodbank_id, donations_date) AS temp
                JOIN food_list ON foodID = food_id
                JOIN foodbanks ON foodbank_id = donation_foodbank_id
                ORDER BY foodbank_id, donor_id, foodID;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
            
#QUERY 5
# Shows FoodBankID, Month, Completed Orders, Pending Orders, Total Orders
class OrderStatus(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" SELECT foodbanks.foodbank_id
                                        , fb_name
                                        , (Month(STR_TO_DATE(order_date, '%c-%e-%Y %H:%i:%s'))) as order_month
                                        , SUM(CASE WHEN o_status = 'completed' THEN 1 ELSE 0 END) AS CompletedOrders
                                        , COUNT(*) - SUM(CASE WHEN o_status = 'completed' THEN 1 ELSE 0 END) AS PendingOrders
                                        , COUNT(*) as TotalOrders
                                FROM orders
                                JOIN foodbanks
                                ON o_foodbank_id = foodbanks.foodbank_id
                                GROUP BY order_month, foodbanks.foodbank_id
                                ORDER BY foodbanks.foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

#QUERY 5
# Shows Customer Addresses
class CustomerAddresses(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT * FROM feed_the_hungry.customer_delivery;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 6
# Shows DELIVERIES
class Deliveries(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                        SELECT ctm_first_name
                                , ctm_last_name
                                , ctm_phone
                                , ctm_address1
                                , ctm_address2
                                , ctm_city
                                , ctm_state
                                , ctm_zipcode
                                , Sum(Total_Items) as Total_Items
                                , delivery_note
                                , delivery_date
                                , fb_name

                        FROM
                            (SELECT o_id
                                    , o_customer_id
                                    , o_foodbank_id
                                    , COUNT(TRIM('"' FROM CAST(json_extract(order_list, val) AS CHAR))) AS Total_Items
                                    , delivery_note
                                    , delivery_date
                            FROM
                            orders
                            JOIN
                            numbers
                            ON JSON_LENGTH(order_list) >= n
                            WHERE o_status = "pending"
                            GROUP BY o_id) temp
                        JOIN customer
                        ON
                        o_customer_id = ctm_id
                        JOIN foodbanks
                        ON
                        o_foodbank_id = foodbank_id
                        GROUP BY delivery_date;
                                            """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 7
class OrderDetails(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                        SELECT concat(IFNULL(ctm_first_name, ''), SPACE(1), IFNULL(ctm_last_name, '')) as customer_name
                                , ctm_phone
                                , concat(IFNULL(ctm_address1, ''), SPACE(1), IFNULL(ctm_address2, ''), SPACE(1), IFNULL(ctm_city, ''), SPACE(1), IFNULL(ctm_state,''), SPACE(1), IFNULL(fb_zipcode, '')) as customer_address
                                , sum(Total_Items) as Total_Items
                                , round(sum(Total_Items*fl_value_in_dollars),2) AS Total_Value
                                , fb_name
                                , concat(fb_address1, SPACE(1) ,fb_city, SPACE(1), fb_state, SPACE(1), fb_zipcode) as foodbank_address
                                , o_delivery_pickup
                                , fb_latitude
                                , fb_longitude
                                , delivery_note
                                , delivery_date
                                , order_date

                        FROM
                            (SELECT o_id
                                    , o_customer_id
                                    , o_foodbank_id
                                    , COUNT(TRIM('"' FROM CAST(json_extract(order_list, val) AS CHAR))) AS Total_Items
                                    , trim('"' FROM cast(json_extract(order_list, val) as CHAR)) AS foodID
                                    , delivery_note
                                    , delivery_date
                                    , o_delivery_pickup
                                    , order_date
                            FROM
                            orders
                            JOIN
                            numbers
                            ON JSON_LENGTH(order_list) >= n
                            GROUP BY o_id, foodID, o_foodbank_id) temp
                        JOIN customer ON o_customer_id = ctm_id
                        JOIN foodbanks ON o_foodbank_id = foodbank_id
                        JOIN food_list ON food_id = foodID
                        GROUP BY o_id;
                                            """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 8
# QUERY : EXCESS INVENTORY
class ExcessInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT tmp.foodbank_id
                , fb_name
                , food_id
                ,fl_name
                , averageOrder
                , inv_qty
                , excess
            FROM (
                SELECT foodbank_id
                    , fl_name
                    , excessList.food_id
                    , averageOrder
                    , inv_qty
                    , excess
                FROM (
                    SELECT inventory.foodbank_id
                        , food_id
                        , averageOrder
                        , inv_qty
                        , (inv_qty - averageOrder) as excess from (
                                    SELECT o_foodbank_id
                        , foodID
                        , (count(foodID)/3) as averageOrder from(
                                        SELECT *
                        , trim('"' from cast(json_extract(order_list, val) as CHAR)) AS foodID
                            FROM orders
                            JOIN numbers on JSON_LENGTH(order_list) >= n
                            WHERE DATE(STR_TO_DATE(order_date, '%c-%e-%Y %H:%i:%s')) < '2021-07-04') temp
                        GROUP BY foodID, o_foodbank_id) ordercount
                    INNER JOIN inventory on foodID = food_id and ordercount.o_foodbank_id = inventory.foodbank_id
                    WHERE inv_qty > averageOrder)
                AS excessList
                LEFT JOIN food_list ON food_list.food_id = excessList.food_id)
            AS tmp
            LEFT JOIN foodbanks ON foodbanks.foodbank_id = tmp.foodbank_id;

            """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 9
# QUERY : LOW INVENTORY
class LowInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                SELECT tmp.foodbank_id
                    , fb_name
                    , food_id
                    ,fl_name
                    , averageOrder
                    , inv_qty
                    , excess
                FROM (
                    SELECT foodbank_id
                        , fl_name
                        , excessList.food_id
                        , averageOrder
                        , inv_qty
                        , excess
                    FROM (
                        SELECT inventory.foodbank_id
                            , food_id
                            , averageOrder
                            , inv_qty
                            , (inv_qty - averageOrder) as excess from (
                                        SELECT o_foodbank_id
                            , foodID
                            , (count(foodID)/3) as averageOrder from(
                                            SELECT *
                            , trim('"' from cast(json_extract(order_list, val) as CHAR)) AS foodID
                                FROM orders
                                JOIN numbers on JSON_LENGTH(order_list) >= n
                                WHERE DATE(STR_TO_DATE(order_date, '%c-%e-%Y %H:%i:%s')) < '2021-07-04') temp
                            GROUP BY foodID, o_foodbank_id) ordercount
                        INNER JOIN inventory on foodID = food_id and ordercount.o_foodbank_id = inventory.foodbank_id
                        WHERE inv_qty < averageOrder)
                    AS excessList
                    LEFT JOIN food_list ON food_list.food_id = excessList.food_id)
                AS tmp
                LEFT JOIN foodbanks ON foodbanks.foodbank_id = tmp.foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 10
# QUERY : NO INVENTORY
class NoInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT fl.foodbank_id
                , fb_name
                , fl.food_id
                , fl_name
                , fl_image
            FROM (
                SELECT * FROM foodbanks, food_list)
            AS fl
            LEFT JOIN inventory i
            ON fl.foodbank_id = i.foodbank_id AND fl.food_id = i.food_id
            WHERE inv_qty IS NULL or inv_qty = 0
            ORDER BY fl.foodbank_id, fl.food_id;
                        """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 11
# QUERY : Food Images
class FoodImages(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT food_id
                , fl_name
                , fl_image
            FROM food_list;
            """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 12
# QUERY : Inventory
class Inventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT fb_name
                    , temp.foodbank_id
                    , temp.food_id
                    , fl_name AS food_name
                    , SUM(inv_qty) as Quantity
                    , fl_image
            FROM
                    (SELECT f.foodbank_id
                            , fb_name
                            , food_id
                            , inv_qty
                    FROM inventory i
                    JOIN foodbanks f
                    ON i.foodbank_id = f.foodbank_id) temp
            JOIN food_list f
            ON f.food_id = temp.food_id
            GROUP BY temp.foodbank_id, f.food_id
            ORDER BY temp.foodbank_id;

                        """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 13
# Customer Order by Foodbank
class CustomerOrderValue(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                    SELECT ctm_id
                            , ctm_first_name
                            , ctm_last_name
                            , o_foodbank_id
                            , fb_name
                            , round(sum(TotalQty*fl_value_in_dollars),2) AS Total_Value
                    FROM (
                            SELECT o_foodbank_id
                                    , o_id
                                    , o_customer_id
                                    , trim('"' FROM cast(json_extract(order_list, val) as CHAR)) AS foodID
                                    , count(trim('"' FROM cast(json_extract(order_list, val) as CHAR))) AS TotalQty
                            FROM orders JOIN numbers ON JSON_LENGTH(order_list) >= n
                            group by o_customer_id, foodID, o_foodbank_id) AS temp
                                
                    JOIN food_list ON food_id = foodID
                    JOIN foodbanks f ON o_foodbank_id = foodbank_id
                    JOIN customer  ON o_customer_id = ctm_id
                    GROUP BY o_customer_id, o_foodbank_id;
                    """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 14
# New Customers by Month by FoodBank
class NewCustomersbyFoodbank(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                    SELECT  foodbank_id
                            , fb_name
                            , MONTH(dates) AS signup_month
                            , COUNT(o_customer_id) AS new_customers
                    FROM (
                            SELECT  o_foodbank_id
                                    , o_customer_id
                                    , DATE(STR_TO_DATE(min(order_date), '%c-%e-%Y %H: %i:%s')) AS dates 
                            FROM orders 
                            GROUP BY o_foodbank_id, o_customer_id
                            ORDER BY o_foodbank_id  , order_date ASC) 
                            AS temp
                    JOIN foodbanks f ON o_foodbank_id = foodbank_id 
                    GROUP BY signup_month, fb_name ORDER BY signup_month;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 15
# Customer Info
class Customers(Resource):
    def get(self):

        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT * FROM customer;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)
            
# QUERY 16
# Foodbank info
class Foodbanks(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
            SELECT * FROM feed_the_hungry.foodbanks;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 17
# Foodbank Info
class FoodBankInfoWithInventory(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
               SELECT fb_name
                    , temp.foodbank_id
                    , fb_tag_line
                    , foodbank_address
                    , fb_monday_time
                    , fb_tuesday_time
                    , fb_wednesday_time
                    , fb_thursday_time
                    , fb_friday_time
                    , fb_saturday_time
                    , fb_sunday_time
                    , temp.food_id
                    , fl_name AS food_name
                    , SUM(inv_qty) as quantity
                    , fl_image
                    , fl_amount
                    , fl_value_in_dollars
                    , fl_package_type
                    , fl_brand
                    , fl_food_type
                    , fb_logo
                        , fb_total_limit
                        , temp.limit
                    ,  fb_longitude
                    , fb_latitude
                        , temp.delivery_pickup
                FROM
                (SELECT i.foodbank_id
                        , fb_name
                        , i.food_id
                        , inv_qty
                        , fb_tag_line
                        , concat(fb_address1, SPACE(1) ,fb_city, SPACE(1), fb_state, SPACE(1), fb_zipcode) as foodbank_address
                        , fb_monday_time
                        , fb_tuesday_time
                        , fb_wednesday_time
                        , fb_thursday_time
                        , fb_friday_time
                        , fb_saturday_time
                        , fb_sunday_time
                        , fb_logo
                        , fb_total_limit
                        , i.limit
                        ,  fb_longitude
                        , fb_latitude
                        , i.delivery_pickup

                FROM
                inventory i
                JOIN foodbanks  f
                ON f.foodbank_id = i.foodbank_id) temp
                JOIN food_list f
                ON temp.food_id = f.food_id
                GROUP BY temp.foodbank_id, f.food_id
                ORDER BY temp.foodbank_id;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 18
class DonationsByDate(Resource):
      def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" SELECT DATE(donation_date) AS date,
                                    count(*) AS num_donations,
                                    SUM(donation_qty*donation_food_value) AS total_value
                                FROM donations_new
                                GROUP BY DATE(donation_date);""", 'get', conn)           

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 19
class DeliveryRoute(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()
            items = execute(""" SELECT * FROM feed_the_hungry.multi_driver_output;""", 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

def sendOrderEmail(customer_id, conn, order_list):
    try:
        response = {}

        query = "SELECT * FROM customer WHERE ctm_id = \'" + customer_id + "\';"
        query_response = execute(query, 'get', conn)

        email = query_response['result'][0]['ctm_email']

        body = ""


        for i in range(len(order_list)):

                meal_id = order_list[i]["meal_id"]
                quantity = order_list[i]["qty"]
                quantity = int(quantity)

                qry = """SELECT fl_name FROM food_list WHERE food_id = \'"""+meal_id+"""\';"""
                qrt_result = execute(qry, 'get', conn)
                food_name = qrt_result['result'][0]['fl_name']

            
                body = body + str(food_name) + " " + str(quantity) + "\n"

        msg = Message("Email Verification",
                          sender='fthtesting@gmail.com', recipients=[email])
        msg.body = "We confirmed the order of following items.\n{} ".format(
            body)

        print(msg.body)

        mail.send(msg)

        return response
    except:
        print("Could not send order confirmation email.")
        return None

# QUERY 20
class addOrder(Resource):
    # HTTP method POST
    def post(self):
        response = {}
        items = []
        try:
            conn = connect()

            data = request.get_json(force=True)

            customer_id = data['customer_id']
            phone = data['phone']
            street = data['street']
            city = data['city']
            state = data['state']
            zipcode = data['zipcode']
            total_cost = data['totalAmount']
            delivery_note = data['delivery_note']
            foodbankId = data['kitchen_id']
            longitude = data["longitude"]
            latitude = data["latitude"]
            delivery_date = data["delivery_date"]
            order_type = data["order_type"]
            foodList = data['ordered_items']
            address = street +" " + city + " " + state + " " + zipcode
            status = 'pending'
            timeStamp = (datetime.now()).strftime("%m-%d-%Y %H:%M:%S")
            print(timeStamp)
            list = []

            for i in range(len(foodList)):

                meal_id = foodList[i]["meal_id"]
                quantity = foodList[i]["qty"]
                quantity = int(quantity)
                for qty in range(quantity):
                    list.append(meal_id)
                query = """SELECT inv_qty FROM inventory WHERE food_id = \'"""+meal_id+"""\' AND foodbank_id = \'"""+foodbankId+"""\';"""
                original_quantity = execute(query, 'get', conn)
                original_quantity = original_quantity['result'][0]['inv_qty']
            
                new_quantity = original_quantity - quantity
                query1 = """UPDATE inventory
                                SET inv_qty = """ +str(new_quantity)+ """                       
                                WHERE food_id = \'"""+meal_id+"""\' AND foodbank_id = \'"""+foodbankId+"""\';""";
                execute(query1, 'get', conn)

            list = json.dumps(list)

            queries = ["CALL get_order_id;"]

            NewUserIDresponse = execute(queries[0], 'get', conn)
            NewUserID = NewUserIDresponse['result'][0]['new_id']

            queries.append( """ INSERT INTO orders
                                (
                                    o_id,
                                    o_customer_id,
                                    o_foodbank_id,
                                    order_list,
                                    o_status,
                                    delivery_note,
                                    delivery_date,
                                    o_total_cost,
                                    order_date,
                                    o_latitude,
                                    o_longitude,
                                    o_delivery_pickup,
                                    order_address
                                )
                                VALUES
                                (
                                    \'""" + NewUserID + """\'
                                    , \'""" + customer_id + """\'
                                    , \'""" + foodbankId + """\'
                                    , \'""" + list + """\'
                                    , \'""" + status + """\'
                                    ,  \'""" + delivery_note + """\'
                                    , \'""" + delivery_date + """\'
                                    , \'""" +  str(total_cost) + """\'
                                    , \'""" + timeStamp + """\'
                                    , \'""" +  str(latitude) + """\'
                                    , \'""" +  str(longitude) + """\'
                                    , \'""" + order_type + """\'
                                    , \'""" +  address + """\');""")

            response['confirmation_email_log'] = sendOrderEmail(customer_id, conn, foodList)

            items = execute(queries[1], 'post', conn)
            response['message'] = 'successful'
            response['result'] = {"order_id": NewUserID}


            return response, 200
        except:
            print("Error happened while Inserting order")
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# QUERY 21
class addCustomer(Resource):
    # HTTP method POST
    def post(self):
        response = {}
        items = []
        try:

            conn = connect()

            data = request.get_json(force=True)

            first_name = data['first_name']
            last_name = data['last_name']
            address1 = data['address1']
            address2 = data['address2']
            city = data['city']
            state = data['state']
            zipcode = data['zipcode']
            phone = data['phone']
            email = data['email']
            # address = street +" " + city + " " + state + " " + zipcode
            timeStamp = (datetime.now()).strftime("%m-%d-%Y %H:%M:%S")


            queries = ["CALL get_customer_id;"]

            NewUserIDresponse = execute(queries[0], 'get', conn)
            NewUserID = NewUserIDresponse['result'][0]['new_id']

            queries.append( """ INSERT INTO customer
                                (
                                    ctm_id,
                                    ctm_first_name,
                                    ctm_last_name,
                                    ctm_address1,
                                    ctm_address2,
                                    ctm_city,
                                    ctm_state,
                                    ctm_zipcode,
                                    ctm_phone,
                                    ctm_email,
                                    ctm_join_date
                                )
                                VALUES
                                (
                                    \'""" + NewUserID + """\'
                                    , \'""" + first_name + """\'
                                    , \'""" + last_name + """\'
                                    , \'""" + address1 + """\'
                                    , \'""" + address2 + """\'
                                    ,  \'""" + city + """\'
                                    , \'""" + state + """\'
                                    , \'""" +  zipcode + """\'
                                    , \'""" + phone + """\'
                                    , \'""" +  email + """\'
                                    , \'""" +  timeStamp + """\');""")

            items = execute(queries[1], 'post', conn)
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            print("Error happened while Inserting new customer")
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 22
# class SignUp(Resource):
#     # HTTP method POST

#     def post(self):
#         response = {}
#         items = []
#         try:
#             conn = connect()
#             data = request.get_json(force=True)


#             first_name = data['first_name']
#             last_name = data['last_name']
#             address1 = data['address1']
#             address2 = data['address2']
#             city = data['city']
#             state = data['state']
#             zipcode = data['zipcode']
#             phone = data['phone']
#             email = data['email']
#             timeStamp = (datetime.now()).strftime("%m-%d-%Y %H:%M:%S")

#             print("data fetch completed")

#             queries = ["CALL get_customer_id;"]

#             NewUserIDresponse = execute(queries[0], 'get', conn)
#             NewUserID = NewUserIDresponse['result'][0]['new_id']

#             queries.append( """ INSERT INTO customer
#                                 (
#                                     ctm_id,
#                                     ctm_first_name,
#                                     ctm_last_name,
#                                     ctm_address1,
#                                     ctm_address2,
#                                     ctm_city,
#                                     ctm_state,
#                                     ctm_zipcode,
#                                     ctm_phone,
#                                     ctm_email,
#                                     ctm_join_date
#                                 )
#                                 VALUES
#                                 (
#                                     \'""" + NewUserID + """\'
#                                     , \'""" + first_name + """\'
#                                     , \'""" + last_name + """\'
#                                     , \'""" + address1 + """\'
#                                     , \'""" + address2 + """\'
#                                     ,  \'""" + city + """\'
#                                     , \'""" + state + """\'
#                                     , \'""" +  zipcode + """\'
#                                     , \'""" + phone + """\'
#                                     , \'""" +  email + """\'
#                                     , \'""" +  timeStamp + """\');""")

#             DatetimeStamp = getNow()
#             salt = getNow()
#             hashed = sha512((data['password'] + salt).encode()).hexdigest()

#             print("hashing completed")

#             queries.append("""
#                 INSERT INTO passwords
#                 (
#                     ctm_id,
#                     pwd_hash,
#                     pwd_salt,
#                     pwd_hash_algorithm,
#                     pwd_created,
#                     pwd_last_changed
#                 )
#                 VALUES
#                 (
#                     \'""" + NewUserID + """\',
#                     \'""" + hashed + """\',
#                     \'""" + salt + """\',
#                     \'SHA512\',
#                     \'""" + DatetimeStamp + """\',
#                     \'""" + DatetimeStamp + "\');")

#             usnInsert = execute(queries[1], 'post', conn)

#             if usnInsert['code'] != 281:
#                 response['message'] = 'Request failed.'
#                 response['result'] = 'Internal server error (Customer write).'

#                 query = """
#                     SELECT ctm_email FROM customer
#                     WHERE ctm_email = \'""" + email + "\';"

#                 emailExists = execute(query, 'get', conn)

#                 if emailExists['code'] == 280 and len(emailExists['result']) > 0:
#                     statusCode = 400
#                     response['result'] = 'Email address taken.'
#                 else:
#                     statusCode = 500
#                     response['result'] = 'Internal server error.'

#                 response['code'] = usnInsert['code']
#                 return response, statusCode

#             pwInsert = execute(queries[2], 'post', conn)

#             if pwInsert['code'] != 281:
#                 response['message'] = 'Request failed.'
#                 response['result'] = 'Internal server error (Password write).'
#                 response['code'] = pwInsert['code']

#                 # Make sure to delete signed up user
#                 # New user was added to db from first MySQL cmd
#                 query = """
#                     DELETE FROM customer
#                     WHERE ctm_email = \'""" + email + "\';"

#                 deleteUser = execute(query, 'post', conn)

#                 # Handle error for successful user account signup
#                 # but failed password storing to the db
#                 if deleteUser['code'] != 281:
#                     response[
#                         'WARNING'] = "This user was signed up to the database but did not properly store their password. Their account cannot be logged into and must be reset by a system administrator."
#                     response['code'] = 590

#                 return response, 500

#             # this part using for testing email verification

#             token = json.dumps(email)
#             msg = Message("Email Verification",
#                           sender='fthtesting@gmail.com', recipients=[email])

#             print(token)
#             print(hashed)
#             link = url_for('confirm', token=token,
#                            hashed=hashed, _external=True)
#             msg.body = "Click on the link {} to verify your email address.".format(
#                 link)

#             mail.send(msg)
#             # email verification testing s ended here...

#             response['message'] = 'Request successful. An email has been sent and need to verify.'
#             response['code'] = usnInsert['code']
#             response['first_name'] = first_name
#             response['user_uid'] = NewUserID

            

#             print(response)
#             return response, 200
#         except:
#             print("Error happened while Sign Up")
#             raise BadRequest('Request failed, please try again later.')
#         finally:
#             disconnect(conn)


class SignUp(Resource):
    # HTTP method POST

    def post(self):
        response = {}
        items = []
        try:
            conn = connect()
            data = request.get_json(force=True)

            user_is_customer = data['user_is_customer']
            user_is_donor = data['user_is_donor']
            user_is_admin = data['user_is_admin']
            user_is_foodbank = data['user_is_foodbank']
            first_name = data['first_name']
            last_name = data['last_name']
            address1 = data['address1']
            address2 = data['address2']
            city = data['city']
            state = data['state']
            zipcode = data['zipcode']
            phone = data['phone']
            email = data['email']
            timeStamp = (datetime.now()).strftime("%m-%d-%Y %H:%M:%S")

            print(data)

            print("data fetch completed")

            queries = ["CALL get_user_id;"]

            NewUserIDresponse = execute(queries[0], 'get', conn)
            NewUserID = NewUserIDresponse['result'][0]['new_id']

            print("got new id")

            queries.append( """ INSERT INTO users
                                (
                                    user_id,
                                    user_is_customer,
                                    user_is_donor,
                                    user_is_admin,
                                    user_is_foodbank,
                                    user_first_name,
                                    user_last_name,
                                    user_address1,
                                    user_address2,
                                    user_city,
                                    user_state,
                                    user_zipcode,
                                    user_phone,
                                    user_email,
                                    user_join_date
                                )
                                VALUES
                                (
                                    \'""" + NewUserID + """\'
                                    , \'""" + str(user_is_customer) + """\'
                                    , \'""" + str(user_is_donor) + """\'
                                    , \'""" + str(user_is_admin) + """\'
                                    , \'""" + str(user_is_foodbank) + """\'
                                    , \'""" + first_name + """\'
                                    , \'""" + last_name + """\'
                                    , \'""" + address1 + """\'
                                    , \'""" + address2 + """\'
                                    ,  \'""" + city + """\'
                                    , \'""" + state + """\'
                                    , \'""" +  zipcode + """\'
                                    , \'""" + phone + """\'
                                    , \'""" +  email + """\'
                                    , \'""" +  timeStamp + """\');""")

           

            print("insert query done")

            DatetimeStamp = getNow()
            salt = getNow()
            hashed = sha512((data['password'] + salt).encode()).hexdigest()

            print("hashing completed")

            queries.append("""
                INSERT INTO passwords
                (
                    user_id,
                    pwd_hash,
                    pwd_salt,
                    pwd_hash_algorithm,
                    pwd_created,
                    pwd_last_changed
                )
                VALUES
                (
                    \'""" + NewUserID + """\',
                    \'""" + hashed + """\',
                    \'""" + salt + """\',
                    \'SHA512\',
                    \'""" + DatetimeStamp + """\',
                    \'""" + DatetimeStamp + "\');")

            usnInsert = execute(queries[1], 'post', conn)

            if usnInsert['code'] != 281:
                response['message'] = 'Request failed.'
                response['result'] = 'Internal server error (Customer write).'

                query = """
                    SELECT user_email FROM users
                    WHERE user_email = \'""" + email + "\';"

                emailExists = execute(query, 'get', conn)

                if emailExists['code'] == 280 and len(emailExists['result']) > 0:
                    statusCode = 400
                    response['result'] = 'Email address taken.'
                else:
                    statusCode = 500
                    response['result'] = 'Internal server error.'

                response['code'] = usnInsert['code']
                return response, statusCode

            pwInsert = execute(queries[2], 'post', conn)

            if pwInsert['code'] != 281:
                response['message'] = 'Request failed.'
                response['result'] = 'Internal server error (Password write).'
                response['code'] = pwInsert['code']

                # Make sure to delete signed up user
                # New user was added to db from first MySQL cmd
                query = """
                    DELETE FROM users
                    WHERE user_email = \'""" + email + "\';"

                deleteUser = execute(query, 'post', conn)

                # Handle error for successful user account signup
                # but failed password storing to the db
                if deleteUser['code'] != 281:
                    response[
                        'WARNING'] = "This user was signed up to the database but did not properly store their password. Their account cannot be logged into and must be reset by a system administrator."
                    response['code'] = 590

                return response, 500

            # this part using for testing email verification

            token = json.dumps(email)
            msg = Message("Email Verification",
                          sender='fthtesting@gmail.com', recipients=[email])

            print(token)
            print(hashed)
            link = url_for('confirm', token=token,
                           hashed=hashed, _external=True)
            msg.body = "Click on the link {} to verify your email address.".format(
                link)

            mail.send(msg)
            # email verification testing s ended here...

            response['message'] = 'Request successful. An email has been sent and need to verify.'
            response['code'] = usnInsert['code']
            response['first_name'] = first_name
            response['user_uid'] = NewUserID

            

            print(response)
            return response, 200
        except:
            print("Error happened while Sign Up")
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# confirmation page
@app.route('/api/v2/confirm/<token>/<hashed>', methods=['GET'])
def confirm(token, hashed):
    try:
        email = json.loads(token)  # max_age = 86400 = 1 day
        # marking email confirmed in database, then...
        conn = connect()
        query = """UPDATE users SET user_email_verified = 1 WHERE user_email = \'""" + \
                email + """\';"""
        update = execute(query, 'post', conn)
        if update.get('code') == 281:
            # redirect to login page
            # Mofify for FTH
            return redirect('http://preptoyourdoor.netlify.app/login/{}/{}'.format(email, hashed))
        else:
            print("Error happened while confirming an email address.")
            error = "Confirm error."
            err_code = 401  # Verification code is incorrect
            return error, err_code
    except (SignatureExpired, BadTimeSignature) as err:
        status = 403  # forbidden
        return str(err), status
    finally:
        disconnect(conn)

def ipVersion(ip):
    if '.' in ip:
        return 'IPv4'
    elif ':' in ip:
        return 'IPv6'
    else:
        return 'unknown'

# QUERY 25
def LogLoginAttempt(data, conn):
    try:
        response = {}

        login_id_res = execute("CALL get_login_log_id;", 'get', conn)
        login_id = login_id_res['result'][0]['new_id']
        # Generate random session ID

        if data["auth_success"] is "TRUE":
            session_id = "\'" + sha512(getNow().encode()).hexdigest() + "\'"
        else:
            session_id = "NULL"
        sql = """
            INSERT INTO login_log (
                login_attempt
                , login_password
                , login_ctm_id
                , ip_address
                , ip_version
                , browser_type
                , attempt_datetime
                , success_bool
                , session_id
            )
            VALUES
            (
                \'""" + login_id + """\'
                , \'""" + data["attempt_hash"] + """\'
                , \'""" + data["ctm_id"] + """\'
                , \'""" + data["ip_address"] + """\'
                , \'""" + ipVersion(data["ip_address"]) + """\'
                , \'""" + data["browser_type"] + """\'
                , \'""" + getNow() + """\'
                , \'""" + data["auth_success"] + """\'
                , """ + session_id + """
            );
            """
        log = execute(sql, 'post', conn)

        if session_id != "NULL":
            session_id = session_id[1:-1]
            print(session_id)

        response['session_id'] = session_id
        response['login_id'] = login_id

        return response
    except:
        print("Could not log login attempt.")
        return None

# QUERY 25
class Login(Resource):

    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            email = data['email']
            password = data['password']

            print("starting Login")


            # if data.get('ip_address') == None:
            #     response['message'] = 'Request failed, did not receive IP address.'
            #     return response, 400
            # if data.get('browser_type') == None:
            #     response['message'] = 'Request failed, did not receive browser type.'
            #     return response, 400


            queries = [
                """ SELECT
                        user_id,
                        user_is_customer,
                        user_is_donor,
                        user_is_admin,
                        user_is_foodbank,
                        user_first_name,
                        user_last_name,
                        user_address1,
                        user_address2,
                        user_city,
                        user_state,
                        user_zipcode,
                        user_phone,
                        user_email,
                        user_join_date,
                        user_email_verified
                    FROM users""" +
                "\nWHERE user_email = " + "\'" + email + "\';"]

            print("get user id query write")

            items = execute(queries[0], 'get', conn)
            user_uid = items['result'][0]['user_id']

            print("get user id query done")

            queries.append(
                "SELECT * FROM passwords WHERE user_id = \'" + user_uid + "\';")
            password_response = execute(queries[1], 'get', conn)
            salt = password_response['result'][0]['pwd_salt']

            hashed = sha512((password + salt).encode()).hexdigest()



            if hashed == password_response['result'][0]['pwd_hash']:
                print("Successful authentication.")
                response['message'] = 'Request successful.'
                response['result'] = items
                response['auth_success'] = True
                httpCode = 200
            else:
                print("Wrong password.")
                response['message'] = 'Request failed, wrong password.'
                response['auth_success'] = False
                httpCode = 401


            login_attempt = {
                'ctm_id': user_uid,
                'attempt_hash': hashed,
                'ip_address': "68.78.203.151",
                'browser_type': "Chrome",
            }

            # 'ip_address': data['ip_address'],
            # 'browser_type': data['browser_type'],

            if response['auth_success']:
                login_attempt['auth_success'] = 'TRUE'
            else:
                login_attempt['auth_success'] = 'FALSE'

            response['login_attempt_log'] = LogLoginAttempt(
                login_attempt, conn)

            return response, httpCode
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 26
class FoodBankInfoWithInventoryNew(Resource):
    def get(self, foodbank):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                            SELECT * FROM 
                                (SELECT i.foodbank_id
                                        , fb_name
                                        , fb_tag_line
                                        , concat(fb_address1, SPACE(1) ,fb_city, SPACE(1), fb_state, SPACE(1), fb_zipcode) as foodbank_address
                                        , fb_monday_time
                                        , fb_tuesday_time
                                        , fb_wednesday_time
                                        , fb_thursday_time
                                        , fb_friday_time
                                        , fb_saturday_time
                                        , fb_sunday_time
                                        , fb_logo
                                        , fb_total_limit AS max_checkout_items
                                        , fb_longitude
                                        , fb_latitude
                                        , i.food_id
                                        , fl_name as food_name
                                        , inv_qty as quantity
                                        , i.limit as food_id_limit
                                        , i.delivery_pickup
                                        , fl_food_type
                                        , fl_image
                                        , concat(fl_amount, " ", fl_unit) as food_unit
                                        , fl_value_in_dollars
                                        , fl_package_type
                                        , fl_brand
                                        , fl_type
                            FROM
                            inventory i
                            JOIN foodbanks  f
                            ON f.foodbank_id = i.foodbank_id
                            JOIN food_list fl
                            ON i.food_id = fl.food_id
                            GROUP BY f.foodbank_id, fl.food_id
                            ORDER BY f.foodbank_id
                            ) t
                        where foodbank_id = \'""" +  foodbank + """\' and quantity > 0;
                        """, 'get', conn)


            days = ['fb_monday_time', 'fb_tuesday_time', 'fb_wednesday_time', 'fb_thursday_time', 'fb_friday_time','fb_saturday_time', 'fb_sunday_time']
            for day in days:
                for i in range(len(items['result'])):
                    if(items['result'][i][day] is not None):
                        times = json.loads(items['result'][i][day])
                        items['result'][i][day + '_delivery'] =  times['delivery']
                        items['result'][i][day + '_order'] =  times['order']
                        del items['result'][i][day]
                    else:
                        items['result'][i][day + '_delivery/order'] = 'Closed'
                        del items['result'][i][day]

            inventory = []
            for i in range(len(items['result'])):
                dict = {}
                dict['food_id'] = items['result'][i]['food_id']
                dict['food_name'] = items['result'][i]['food_name']
                dict['quantity'] = items['result'][i]['quantity']
                dict['fl_image'] = items['result'][i]['fl_image']
                dict['food_unit'] = str(items['result'][i]['food_unit'])
                dict['fl_value_in_dollars'] = items['result'][i]['fl_value_in_dollars']
                dict['fl_package_type'] = items['result'][i]['fl_package_type']
                dict['fl_brand'] = items['result'][i]['fl_brand']
                dict['fl_food_type'] = items['result'][i]['fl_food_type']
                dict['food_id_limit'] = items['result'][i]['food_id_limit']
                dict['delivery_pickup'] = items['result'][i]['delivery_pickup']
                dict['fl_type'] = items['result'][i]['fl_type']
                inventory.append(dict)
                items['result'][i]['inventory'] = inventory 

                del items['result'][i]['food_id']
                del items['result'][i]['food_name']
                del items['result'][i]['quantity']
                del items['result'][i]['fl_image']
                del items['result'][i]['food_unit']
                del items['result'][i]['fl_value_in_dollars']
                del items['result'][i]['fl_package_type']
                del items['result'][i]['fl_brand']
                del items['result'][i]['fl_food_type']
                del items['result'][i]['food_id_limit']
                del items['result'][i]['delivery_pickup']
                del items['result'][i]['fl_type']

            response['message'] = 'successful'
            response['result'] = items['result'][0]

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

# QUERY 18
class FoodType(Resource):
      def get(self, foodbank, foodtype):
        response = {}
        items = {}
        try:
            conn = connect()

            query = """ SELECT * FROM 
                                    (SELECT i.foodbank_id
                                            , fb_name
                                            , fb_tag_line
                                            , concat(fb_address1, SPACE(1) ,fb_city, SPACE(1), fb_state, SPACE(1), fb_zipcode) as foodbank_address
                                            , fb_monday_time
                                            , fb_tuesday_time
                                            , fb_wednesday_time
                                            , fb_thursday_time
                                            , fb_friday_time
                                            , fb_saturday_time
                                            , fb_sunday_time
                                            , fb_logo
                                            , fb_total_limit AS max_checkout_items
                                            , fb_longitude
                                            , fb_latitude
                                            , i.food_id
                                            , fl_name as food_name
                                            , inv_qty as quantity
                                            , i.limit as food_id_limit
                                            , i.delivery_pickup
                                            , substring_index(substring_index(fl_food_type,';',n),';',-1) AS foodCategory
                                            , fl_image
                                            , concat(fl_amount, " ", fl_unit) as food_unit
                                            , fl_value_in_dollars
                                            , fl_package_type
                                            , fl_brand
                                            , fl_type
                                FROM
                                inventory i
                                JOIN foodbanks  f
                                ON f.foodbank_id = i.foodbank_id
                                JOIN food_list fl
                                ON i.food_id = fl.food_id
                                JOIN numbers 
                                ON char_length(fl_food_type) - char_length(replace(fl_food_type, ';', '')) >= n - 1
                                GROUP BY f.foodbank_id, fl.food_id, foodCategory
                                ORDER BY f.foodbank_id
                                ) t
                            where foodbank_id = \'""" +  foodbank + """\' and quantity > 0 and foodCategory = \'""" +  foodtype + """\';"""
            items = execute(query, 'get', conn)           
            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

class SocialSignUp(Resource):
    # HTTP method POST
    def post(self):
        response = {}
        try:
            conn = connect()
            data = request.get_json(force=True)

            user_is_customer = data['user_is_customer']
            user_is_donor = data['user_is_donor']
            user_is_admin = data['user_is_admin']
            user_is_foodbank = data['user_is_foodbank']
            first_name = data['first_name']
            last_name = data['last_name']
            address1 = data['address1']
            address2 = data['address2']
            city = data['city']
            state = data['state']
            zipcode = data['zipcode']
            phone = data['phone']
            email = data['email']
            social_media = data['social_media']
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            timeStamp = (datetime.now()).strftime("%m-%d-%Y %H:%M:%S")

            print("Received:", data)

            # Query [0]
            queries = ["CALL get_user_id;"]

            NewUserIDresponse = execute(queries[0], 'get', conn)
            NewUserID = NewUserIDresponse['result'][0]['new_id']

            print("NewUserID:", NewUserID)

            queries.append( """ INSERT INTO users
                                (
                                    user_id,
                                    user_is_customer,
                                    user_is_donor,
                                    user_is_admin,
                                    user_is_foodbank,
                                    user_first_name,
                                    user_last_name,
                                    user_address1,
                                    user_address2,
                                    user_city,
                                    user_state,
                                    user_zipcode,
                                    user_phone,
                                    user_email,
                                    user_join_date
                                )
                                VALUES
                                (
                                    \'""" + NewUserID + """\'
                                    , \'""" + str(user_is_customer) + """\'
                                    , \'""" + str(user_is_donor) + """\'
                                    , \'""" + str(user_is_admin) + """\'
                                    , \'""" + str(user_is_foodbank) + """\'
                                    , \'""" + first_name + """\'
                                    , \'""" + last_name + """\'
                                    , \'""" + address1 + """\'
                                    , \'""" + address2 + """\'
                                    ,  \'""" + city + """\'
                                    , \'""" + state + """\'
                                    , \'""" +  zipcode + """\'
                                    , \'""" + phone + """\'
                                    , \'""" +  email + """\'
                                    , \'""" +  timeStamp + """\');""")


            # Query [2]
            queries.append("""
                INSERT INTO social_accounts
                (
                    user_id,
                    social_email,
                    social_media,
                    social_access_token,
                    social_refresh_token
                )
                VALUES
                (
                    \'""" + NewUserID + """\',
                    \'""" + email + """\',
                    \'""" + social_media + """\',
                    \'""" + access_token + """\',
                    \'""" + refresh_token + "\');")

            usnInsert = execute(queries[1], 'post', conn)

            if usnInsert['code'] != 281:
                response['message'] = 'Request failed.'

                query = """
                    SELECT user_email FROM users
                    WHERE user_email = \'""" + email + "\';"

                emailExists = execute(query, 'get', conn)

                if emailExists['code'] == 280 and len(emailExists['result']) > 0:
                    statusCode = 400
                    response['result'] = 'Email address taken.'
                else:
                    statusCode = 500
                    response['result'] = 'Internal server error.'

                response['code'] = usnInsert['code']
                print(response['message'],
                      response['result'], usnInsert['code'])
                return response, statusCode

            socInsert = execute(queries[2], 'post', conn)

            if socInsert['code'] != 281:
                response['message'] = 'Request failed.'

                query = """
                    SELECT social_email FROM social_accounts
                    WHERE social_email = \'""" + email + "\';"

                emailExists = execute(query, 'get', conn)

                if emailExists['code'] == 280 and len(emailExists['result']) > 0:
                    statusCode = 400
                    response['result'] = 'Email address taken.'
                else:
                    statusCode = 500
                    response['result'] = 'Internal server error.'


                response['result'] = 'Could not commit password.'
                print(response['message'],
                      response['result'], socInsert['code'])
                return response, 500

            response['message'] = 'Request successful.'
            response['result'] = {'user_uid': NewUserID}

            print(response)
            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# Social Media Login API


class Social(Resource):

    # HTTP method GET
    def get(self, email):
        response = {}
        try:
            conn = connect()

            queries = [
                """     SELECT
                        user_id,
                        social_email,
                        social_media,
                        social_access_token,
                        social_refresh_token
                    FROM social_accounts WHERE social_email = '""" + email + "';"
            ]

            items = execute(queries[0], 'get', conn)
            response['message'] = 'Request successful.'
            response['result'] = items
            # restest = SocialAccount().get(email)

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


class SocialAccount(Resource):

    # HTTP method POST
    def post(self, user_id):
        response = {}
        try:
            conn = connect()
            #data = request.get_json(force=True)
            queries = [
                """     SELECT
                        user_id,
                        user_is_customer,
                        user_is_donor,
                        user_is_admin,
                        user_is_foodbank,
                        user_first_name,
                        user_last_name,
                        user_address1,
                        user_address2,
                        user_city,
                        user_state,
                        user_zipcode,
                        user_phone,
                        user_email,
                        user_join_date
                    FROM users WHERE user_id = '""" + user_id + "';"]

            items = execute(queries[0], 'get', conn)

            print(items)
            # create a login attempt
            login_attempt = {
                'auth_success': 'TRUE',
                'ctm_id': user_id,
                'attempt_hash': "NULL",
                'ip_address': "68.78.203.151",
                'browser_type': "Chrome",
            }

            response['login_attempt_log'] = LogLoginAttempt(
                login_attempt, conn)

            response['message'] = 'Request successful.'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)


# Define API routes

# Still uses getRdsConn()
# Needs to be converted to V2 APIs
#api.add_resource(Meals, '/api/v1/meals')
#api.add_resource(Accounts, '/api/v1/accounts')

# New APIs, uses connect() and disconnect()
# Create new api template URL

api.add_resource(DonorValuation, '/api/v2/donordonation')
api.add_resource(ItemDonations, '/api/v2/itemdonations')
api.add_resource(TypesOfFood, '/api/v2/foodtypes')
api.add_resource(DonationbyDate, '/api/v2/donation')
api.add_resource(DonationbyFood, '/api/v2/donationFood')


api.add_resource(OrderStatus, '/api/v2/orderstatus')
api.add_resource(CustomerAddresses, '/api/v2/customeraddresses')
api.add_resource(Deliveries, '/api/v2/deliveries')

api.add_resource(CustomerOrderValue, '/api/v2/customervalue')
api.add_resource(NewCustomersbyFoodbank, '/api/v2/newcustomers')
api.add_resource(Customers, '/api/v2/customerinfo')

api.add_resource(ExcessInventory, '/api/v2/excess')
api.add_resource(LowInventory, '/api/v2/low')
api.add_resource(NoInventory, '/api/v2/zero')
api.add_resource(FoodImages, '/api/v2/foodimages')

api.add_resource(Inventory, '/api/v2/inventory')

api.add_resource(Foodbanks, '/api/v2/foodbanks')
api.add_resource(FoodBankInfoWithInventory, '/api/v2/foodbankinfo')

api.add_resource(DonationsByDate, '/api/v2/donationsbydate')
api.add_resource(DeliveryRoute, '/api/v2/deliveryroute')
api.add_resource(addOrder, '/api/v2/add_order')
api.add_resource(addCustomer, '/api/v2/add_customer')
api.add_resource(SignUp, '/api/v2/signup')
api.add_resource(OrderDetails, '/api/v2/orderdetails')
api.add_resource(Login, '/api/v2/login')
api.add_resource(FoodBankInfoWithInventoryNew, '/api/v2/foodbankinfonew/<foodbank>')
api.add_resource(FoodType, '/api/v2/foodtype/<foodbank>/<foodtype>')

api.add_resource(SocialSignUp, '/api/v2/socialsignup')
api.add_resource(Social, '/api/v2/social/<string:email>')
api.add_resource(SocialAccount, '/api/v2/socialacc/<string:user_id>')

# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)
