"""
Class that provides serverless application from a given SAM template
"""
import logging
from typing import Dict, List

from samcli.commands.local.cli_common.user_exceptions import InvalidLayerVersionArn
from samcli.lib.providers.exceptions import InvalidLayerReference
from samcli.lib.utils.colors import Colored
from samcli.lib.utils.packagetype import ZIP, IMAGE
# from .provider import Function, LayerVersion
from .sam_base_provider import SamBaseProvider

LOG = logging.getLogger(__name__)


class SamServerlessApplicationProvider(SamBaseProvider):
    """
    Fetches and returns serverless applications from a SAM Template. The SAM template passed to this provider is assumed
    to be valid, normalized and a dictionary.

    It may or may not contain a function.
    """

    def __init__(self, template_dict, parameter_overrides=None, ignore_code_extraction_warnings=False):
        """
        Initialize the class with SAM template data. The SAM template passed to this provider is assumed
        to be valid, normalized and a dictionary. It should be normalized by running all pre-processing
        before passing to this class. The process of normalization will remove structures like ``Globals``, resolve
        intrinsic functions etc.
        This class does not perform any syntactic validation of the template.

        After the class is initialized, any changes to the ``template_dict`` will not be reflected in here.
        You need to explicitly update the class with new template, if necessary.

        :param dict template_dict: SAM Template as a dictionary
        :param dict parameter_overrides: Optional dictionary of values for SAM template parameters that might want
            to get substituted within the template
        :param bool ignore_code_extraction_warnings: Ignores Log warnings
        """

        self.template_dict = SamServerlessApplicationProvider.get_template(template_dict, parameter_overrides)
        self.ignore_code_extraction_warnings = ignore_code_extraction_warnings
        self.resources = self.template_dict.get("Resources", {})

        LOG.debug("%d resources found in the template", len(self.resources))

        # Store a map of function name to function information for quick reference
        self.functions = self._extract_serverless_applications(self.resources, self.ignore_code_extraction_warnings)

        # self._deprecated_runtimes = {"nodejs4.3", "nodejs6.10", "nodejs8.10", "dotnetcore2.0"}
        self._colored = Colored()

    def get(self, name):
        """
        Returns the application for a given name or LogicalId of the application. Every SAM resource has a logicalId,
        but it may also have a given name. 

        :param string name: Name of the application
        :return ServerlessApplication: namedtuple containing the SeverlessApplication information if function is found.
                          None, if function is not found
        :raises ValueError If name is not given
        """

        if not name:
            raise ValueError("Application name is required")

        for f in self.get_all():
            if f.name == name:
                return f

            if f.applicationname == name:
                return f

        return None

    def get_all(self):
        """
        Yields all the Serverless Applications available in the SAM Template.

        :yields ServerlessApplication: namedtuple containing the application information
        """

        for _, application in self.applications.items():
            yield application

    @staticmethod
    def _extract_serverless_applications(resources, ignore_code_extraction_warnings=False):
        """
        Extracts and returns serverless application information from the given dictionary of SAM/CloudFormation
        resources.

        :param dict resources: Dictionary of SAM/CloudFormation resources
        :param bool ignore_code_extraction_warnings: suppress log statements on code extraction from resources.
        :return dict(string : samcli.commands.local.lib.provider.ServerlessFunction): Dictionary of application LogicalId to the
            ServerlessApplication configuration object
        """

        result = {}

        for name, resource in resources.items():

            resource_type = resource.get("Type")
            resource_properties = resource.get("Properties", {})
            resource_metadata = resource.get("Metadata", None)
            # Add extra metadata information to properties under a separate field.
            if resource_metadata:
                resource_properties["Metadata"] = resource_metadata

            if resource_type == SamServerlessApplicationProvider.SERVERLESS_APPLICATION:
                result[name] = SamServerlessApplicationProvider._convert_sam_serverless_application_resource(
                    name, resource_properties, ignore_code_extraction_warnings=ignore_code_extraction_warnings
                )

            # We don't care about other resource types. Just ignore them

        return result

    @staticmethod
    def _convert_sam_serverless_application_resource(name, resource_properties, ignore_code_extraction_warnings=False):
        """
        Converts a AWS::Serverless::Application resource to a ServerlessApplication configuration usable by the provider.

        Parameters
        ----------
        name str
            LogicalID of the resource 
        resource_properties dict
            Properties of this resource

        Returns
        -------
        samcli.commands.local.lib.provider.ServerlessApplication
            Application configuration
        """
        location = resource_properties.get("Location")

        return SamServerlessApplicationProvider._build_serverless_application_configuration(
            name, location, resource_properties
        )

    @staticmethod
    def _build_serverless_application_configuration(
        name: str, location: str, resource_properties: Dict
    ):
        """
        Builds a ServerlessApplication configuration usable by the provider.

        Parameters
        ----------
        name str
            LogicalID of the resource
        location str
            Representing the location attribute
        resource_properties dict
            Properties of this resource

        Returns
        -------
        samcli.commands.local.lib.provider.ServerlessApplication
            Serverless Application configuration
        """
        return ServerlessApplication(
            name=name,
            location=location
            notification_arns=resource_properties.get("NotificationARNs", ZIP),
            parameters=resource_properties.get("Parameters"),
            tags=resource_properties.get("Tags"),
            timeout=resource_properties.get("TimeoutInMinutes"),
        )
