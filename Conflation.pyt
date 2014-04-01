import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Specific Route Location"
        self.alias = "wsdotspecificlrs"

        # List of tool classes associated with this toolbox
        self.tools = [LocateFeaturesAlongSpecificRoutes]


class LocateFeaturesAlongSpecificRoutes(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Locate Features Along Specific Routes"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        pointFeaturesParam = arcpy.Parameter(
            displayName="Point Features",
            name="point_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        pointFeaturesParam.filter.list = ["Point"]

        routeFeaturesParam = arcpy.Parameter(
            displayName="Route Features",
            name="route_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        routeFeaturesParam.filter.list = ["Polyline"]

        pointUniqueIdParam = arcpy.Parameter(
            displayName="Point Unique ID Field",
            name="point_unique_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        pointUniqueIdParam.parameterDependencies = [pointFeaturesParam.name]
        pointUniqueIdParam.filter.list = ["Short", "Long", "Text", "Double"]

        pointRouteIdFieldParam = arcpy.Parameter(
            displayName="Point Layer Route ID Field",
            name="point_layer_route_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        pointRouteIdFieldParam.parameterDependencies = [pointFeaturesParam.name]
        pointRouteIdFieldParam.filter.list = ["Short", "Long", "Text"]

        routeRouteIdFieldParam = arcpy.Parameter(
            displayName="Route Layer Route ID Field",
            name="route_layer_route_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        routeRouteIdFieldParam.parameterDependencies = [routeFeaturesParam.name]
        routeRouteIdFieldParam.filter.list = ["Short", "Long", "Text"]

        radiusOrToleranceParam = arcpy.Parameter(
            displayName="Radius or Tolerance",
            name="radius_or_tolerance",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")

        outputFCParam = arcpy.Parameter(
            displayName = "Output Feature Class",
            name = "Output Feature Class",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        params = [pointFeaturesParam, routeFeaturesParam, pointUniqueIdParam, pointRouteIdFieldParam, routeRouteIdFieldParam, radiusOrToleranceParam, outputFCParam]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        pointFeatures = parameters[0].valueAsText
        routeFeatures = parameters[1].valueAsText
        pointUniqueId = parameters[2].valueAsText
        pointRouteIdField = parameters[3].valueAsText
        routesRouteIdField = parameters[4].valueAsText
        radiusOrTolerance = parameters[5].valueAsText
        outFeatures = parameters[6].valueAsText
        
        def getUniqueValues(fc, fieldName):
            """Gets a distinct list of route IDs from a feature class.
            :param fc: feature class with route ID information
            :type fc: str
            :param routeIdFieldName: name of the route ID field in fc.
            :type routeIdFieldName: str
            :returns: A list of route IDs
            :rtype: []
            """
            # Get route ids.
            routeIds = []
            lastRouteId = None
            with arcpy.da.SearchCursor(fc, [fieldName], sql_clause=(None, "ORDER BY %s" % fieldName)) as cursor:
                for row in cursor:
                    currentId = row[0]
                    if currentId != lastRouteId:
                        routeIds.append(currentId)
                    lastRouteId = currentId
            return routeIds

        def createInWhereClause(fieldName, values, invert=False, is_number=False):
            whereClause = None
            if invert:
                whereClause = "%s NOT IN (" % fieldName
            else:
                whereClause = "%s IN (" % fieldName
            for v in values:
                if is_number:
                    whereClause = whereClause + "%s," % v
                else:
                    whereClause = whereClause + "'%s'," % v
            whereClause = whereClause.rstrip(",") + ")"
            return whereClause

        def locate_points_along_routes():
            tempTable = arcpy.CreateScratchName("temp", None, "TABLE", "in_memory")
    
            # Locate features along routes
            arcpy.lr.LocateFeaturesAlongRoutes(pointsLayer, routeLayer, routesRouteIdField, radiusOrTolerance, tempTable, out_event_properties, "FIRST", "DISTANCE", "ZERO", "FIELDS")
    
            # Create the output table if it does not already exist.
            try:
                if not arcpy.Exists(outEventTable):
                    arcpy.management.CopyRows(tempTable, outEventTable)
                else: 
                    arcpy.management.Append(tempTable, outEventTable, "TEST")
            except arcpy.ExecuteError as err:
                print err
                raise err
            # Now that the rows have been copied, the temp. table can be deleted.
            arcpy.management.Delete(tempTable)

        try:
            routeIds = getUniqueValues(pointFeatures, pointRouteIdField)

            outEventTable = arcpy.CreateScratchName("events", "", workspace = "in_memory")

            out_event_properties = "%s POINT %s" % ("RID", "MEAS")

            routeLayer = arcpy.CreateScratchName("route", "layer", workspace="in_memory")
            pointsLayer = arcpy.CreateScratchName("point", "layer", workspace="in_memory")
            where = createInWhereClause(routesRouteIdField, routeIds)

            arcpy.management.MakeFeatureLayer(routeFeatures, routeLayer, where, "in_memory")
            arcpy.management.MakeFeatureLayer(pointFeatures, pointsLayer, workspace="in_memory")

            # Delete the output table if it already exists.
            if arcpy.Exists(outEventTable):
                arcpy.management.Delete(outEventTable)

            for routeId in routeIds:
                print "Processing \"%s\"..." % routeId
                # Select the features that match the current route.
                arcpy.management.SelectLayerByAttribute(routeLayer, "NEW_SELECTION", "%s = '%s'" % (routesRouteIdField, routeId))
                arcpy.management.SelectLayerByAttribute(pointsLayer, "NEW_SELECTION", "%s = '%s'" % (pointRouteIdField, routeId))

                locate_points_along_routes()


            # Clear the selection on the points and route layers.
            arcpy.management.SelectLayerByAttribute(routeLayer, "CLEAR_SELECTION")
            arcpy.management.SelectLayerByAttribute(pointsLayer, "CLEAR_SELECTION")

            # Find the nearest route to the points that have not yet been matched.
            matchedPointIds = getUniqueValues(pointsLayer, pointUniqueId)
            where = createInWhereClause(pointUniqueId, matchedPointIds, True, True)
            arcpy.management.SelectLayerByAttribute(pointsLayer, "NEW_SELECTION", where)
            locate_points_along_routes()


            # Create the route event layer.
            eventLayer = arcpy.CreateScratchName("event", workspace="in_memory")
            arcpy.lr.MakeRouteEventLayer(routeLayer, routesRouteIdField, outEventTable, out_event_properties, eventLayer, None, "ERROR_FIELD", "ANGLE_FIELD", "NORMAL", "ANGLE", "LEFT", "POINT")

            arcpy.management.CopyFeatures(eventLayer, outFeatures)

            for item in [routeLayer, pointsLayer, eventLayer, outEventTable]:
                arcpy.management.Delete(item)
        except arcpy.ExecuteError as err:
            print err
            raise err
        finally:
            # Clear all of the temp tables created in the "in_memory" workspace.
            arcpy.management.Delete("in_memory")
        return