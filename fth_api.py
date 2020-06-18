#To run program:  python3 fth_api.py prashant

#README:  if conn error make sure password is set properly in RDS PASSWORD section

#README:  Debug Mode may need to be set to Fales when deploying live (although it seems to be working through Zappa)

#README:  if there are errors, make sure you have all requirements are loaded
#pip3 install flask
#pip3 install flask_restful
#pip3 install flask_cors
#pip3 install Werkzeug
#pip3 install pymysql
#pip3 install python-dateutil


from flask import Flask, request, render_template
from flask_restful import Resource, Api
from flask_cors import CORS

from werkzeug.exceptions import BadRequest, NotFound

from dateutil.relativedelta import *
from decimal import Decimal
from datetime import datetime, date, timedelta
from hashlib import sha512
from math import ceil

import decimal
import sys
import json
import pymysql

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

# DONOR QUERIES - ROHAN

# QUERY 1
# DONATION INFORMATION: FoodBankID, FoodbankName, Donor Name, Total Donations, Donation Date
class DonorValuation(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute("""
                        SELECT 
                                d.donor_id,
                                donor_first_name,
                                donor_last_name,
                                donation_date,
                                donation_foodbank_id,
                                fb_name,
<<<<<<< HEAD
                                sum(total) totalDonation,
                                sum(food_count) total_qty
=======
                                sum(total) totalDonation
>>>>>>> delivery route
                        FROM (
                            SELECT donation_foodbank_id,
                                    donor_id,
                                    donation_date,
                                    foodID,
<<<<<<< HEAD
                                    count(foodID) AS food_count,
=======
>>>>>>> delivery route
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
<<<<<<< HEAD
                            , TotalDonation AS Donation_Qty
                            , round(TotalDonation * fl_value_in_dollars, 2) totalDonation
=======
                            , TotalDonation
>>>>>>> delivery route
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
<<<<<<< HEAD
                SELECT  foodbank_id
                        , fb_name
                        , fl_type
                        , count(fl_type) AS Donation_Qty
                        , round(count(fl_type) * fl_value_in_dollars, 2) AS totalDonation
=======
                SELECT foodbank_id
                        , fb_name
                        , fl_type
                        , count(fl_type) total
>>>>>>> delivery route
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
<<<<<<< HEAD
                SELECT  foodbank_id
=======
                SELECT foodbank_id
>>>>>>> delivery route
                        , fb_name
                        , donations_date
                        , foodID
                        , quantity
                        , fl_name
<<<<<<< HEAD
                        , round(quantity * fl_value_in_dollars, 2) AS totalDonation
=======
>>>>>>> delivery route
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

            
<<<<<<< HEAD

=======
#QUERY 5
>>>>>>> delivery route
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
                        GROUP BY delivery_date;
                                            """, 'get', conn)

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)



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
                        , fl_unit
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

class DonationsByDate(Resource):
      def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" SELECT DATE(donation_date) AS date,
                                    count(*) AS num_donations,
                                    SUM(donation_qty*donation_food_value) AS total_value
                                FROM Donations_new
                                GROUP BY DATE(donation_date);""", 'get', conn)           

            response['message'] = 'successful'
            response['result'] = items

            return response, 200
        except:
            raise BadRequest('Request failed, please try again later.')
        finally:
            disconnect(conn)

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

# -- Queries end here -------------------------------------------------------------------------------

# Add Comment Here ie Shows All Meal Plan Info
class TemplateApi(Resource):
    def get(self):
        response = {}
        items = {}
        try:
            conn = connect()

            items = execute(""" SELECT
                                *
                                FROM
                                ptyd_meal_plans;""", 'get', conn)

            response['message'] = 'successful'
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

api.add_resource(TemplateApi, '/api/v2/templateapi')
api.add_resource(DonorValuation, '/api/v2/donordonation')
api.add_resource(ItemDonations, '/api/v2/itemdonations')
api.add_resource(TypesOfFood, '/api/v2/foodtypes')
api.add_resource(DonationbyDate, '/api/v2/donation')

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

>>>>>>> delivery route


# Run on below IP address and port
# Make sure port number is unused (i.e. don't use numbers 0-1023)
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4000)
