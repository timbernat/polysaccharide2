'''For querying chemical databases for information about molecules specified by SMILES string and other structures'''

__author__ = 'Timotej Bernat'
__email__ = 'timotej.bernat@colorado.edu'

import logging
LOGGER  = logging.getLogger(__name__)

from typing import Any, ClassVar, Container, Optional, Sequence
from abc import ABC, abstractmethod

from requests import HTTPError

from ..genutils.decorators.classmod import register_abstract_class_attrs, register_subclasses
from ..genutils.importutils.dependencies import modules_installed, MissingPrerequisitePackage


# CUSTOM EXCEPTIONS
class InvalidPropertyError(Exception):
    '''Raised when attempting to query a property that a chemical database service cannot provide'''
    pass

class NullPropertyResponse(Exception):
    '''Raised when a chemical database query doesn't fail BUT returns a NoneType where not allowed'''
    pass

class ChemicalDataQueryFailed(Exception):
    '''Raised when a chemical data query is unfulfilled by a service'''
    pass

# STRATEGIES BASE FOR QUERYING CHEMICAL DATA
@register_subclasses(key_attr='service_name')
@register_abstract_class_attrs('service_name', 'available_properties')
class ChemDBServiceQueryStrategy(ABC):
    '''Implementation of queries from a particular chemical database'''
    @abstractmethod
    def _get_property(self, prop_name : str, representation : str, **kwargs) -> Optional[Any]:
        ...
        
    def validate_property(self, prop_name : str) -> None:
        '''Pre-check to ensure that a property is queryable from a service before attempting HTTP query'''
        if prop_name not in self.available_properties:
            prop_options_str = '\n'.join(sorted(self.available_properties))
            prop_error_msg = f'Cannot query property "{prop_name}" from {self.service_name}'
            LOGGER.error(prop_error_msg) # log briefer error message in cases where the ensuing ValueError is bypassed
            
            raise InvalidPropertyError(f'{prop_error_msg};\nChoose from one of the following property names:\n{prop_options_str}')
        
    def get_property(
            self, 
            prop_name : str, 
            representation : str, 
            namespace : str='smiles',
            keep_first_only : bool=True,
            allow_null_return : bool=False,
            **kwargs
        ) -> Optional[Any]:
        '''Fetch a property associated with a molecule from a chemical database query service'''
        LOGGER.info(f'Sent query request for property "{prop_name}" to {self.service_name}')
        self.validate_property(prop_name=prop_name)
        
        prop_val = self._get_property(prop_name=prop_name, representation=representation, namespace=namespace, **kwargs)
        if (prop_val is not None):
            if keep_first_only and isinstance(prop_val, Container) and not isinstance(prop_val, str): # avoid bug where first char of string response is returned
                prop_val = prop_val[0]
        elif not allow_null_return:
            null_error_msg = f'{self.service_name} returned NoneType "{prop_name}", which is declared invalid by call signature'
            LOGGER.error(null_error_msg)
            
            raise NullPropertyResponse(null_error_msg)
        LOGGER.info(f'Successfully received property "{prop_name}" from {self.service_name}')
                
        return prop_val
    
# CONCRETE IMPLEMENTATIONS OF CHEMICAL DATABASE SERVICE QUERIES
if not modules_installed('cirpy'):
    raise MissingPrerequisitePackage(
        importing_package_name=__spec__.name,
        use_case='Querying the NIH CACTUS Chemical Identifier Resolver (CIR)',
        install_link='https://cirpy.readthedocs.io/en/latest/guide/install.html',
        dependency_name='cirpy',
        dependency_name_formal='CIRpy',
    )
else:
    import cirpy
    
    class NIHCACTUSQueryStrategy(ChemDBServiceQueryStrategy):
        '''
        Implementation of chemical query requests to the NIH's CADD group 
        Cheminformatics Tools and User Services (CACTUS) Chemical Identifier Resolver (CIR)
        '''
        service_name : ClassVar[str] = 'NIH CACTUS CIR'
        _CIR_PROPS : ClassVar[set[str]] = {
            'stdinchikey',
            'stdinchi',
            'smiles',
            'ficts',
            'ficus',
            'uuuuu',
            'hashisy',
            'names',
            'iupac_name',
            'cas',
            'chemspider_id',
            'image',
            'twirl',
            'mw',
            'formula',
            'h_bond_donor_count',
            'h_bond_acceptor_count',
            'h_bond_center_count',
            'rule_of_5_violation_count',
            'rotor_count',
            'effective_rotor_count',
            'ring_count',
            'ringsys_count',
        }
        available_properties : ClassVar[set[str]] = _CIR_PROPS | cirpy.FILE_FORMATS # see official docs for more info: https://cactus.nci.nih.gov/chemical/structure_documentation
        
        def _get_property(self, prop_name : str, representation : str, namespace : str, **kwargs):
            # NOTE: "namespace" is interpreted as a signular resolver method (https://cirpy.readthedocs.io/en/latest/guide/resolvers.html)
            return cirpy.resolve(representation, prop_name, resolvers=[namespace], **kwargs)

if not modules_installed('pubchempy'):
    raise MissingPrerequisitePackage(
        importing_package_name=__spec__.name,
        use_case='Querying the PubChem Compound database',
        install_link='https://pubchempy.readthedocs.io/en/latest/guide/install.html',
        dependency_name='pubchempy',
        dependency_name_formal='PubChemPy',
    )
else:
    import pubchempy as pcp
    
    class PubChemQueryStrategy(ChemDBServiceQueryStrategy):
        '''
        Implementation of chemical query requests to PubChem via the
        PUG REST API (https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest)
        '''
        service_name : ClassVar[str] = 'PubChem'
        available_properties : ClassVar[set[str]] = set(pcp.PROPERTY_MAP.keys()) | set(pcp.PROPERTY_MAP.values())
        
        def _get_property(self, prop_name : str, representation : str, namespace : str, **kwargs) -> Optional[Any]:
            official_prop_name = pcp.PROPERTY_MAP.get(prop_name, prop_name) # this is done internally, but needed here to extract the property value from the final return dict
            try:
                pubchem_result = pcp.get_properties(official_prop_name, identifier=representation, namespace=namespace, **kwargs)
            except pcp.PubChemPyError:
                raise HTTPError # discards some information in return for making Strategy interface oblivious to pubchempy (i.e. in case it is not installed)
            else:
                if pubchem_result:
                    pubchem_result = [
                        query_result[official_prop_name] # extract property value from extraneous CID (and any other) info
                            for query_result in pubchem_result
                                if official_prop_name in query_result # skip if return doesn't contain the info we specifically requested (happens occasionally for some reason)
                    ] 
                return pubchem_result
        
# UTILITY FUNCTIONS EMPLOYING GENERIC STRATEG(Y/IES)
def get_chemical_property(
        prop_name : str, 
        representation : str, 
        namespace : str='smiles',
        keep_first_only : bool=True,
        allow_null_return : bool=False,
        fail_quietly : bool=False,
        services : Optional[Sequence['ChemDBServiceQueryStrategy']]=None,
        **kwargs,
    ) -> Optional[Any]:
    '''Attempt to fetch a molecular property from a variety of chemical database services, either
    provided manually (in the order they should be checked) or ALL implemented service queries by default
    
    Will return the first valid returned result or, if all services fail, raise Exception
    '''
    # determine services which should be queried
    if services is None:
        services = [chem_query_strat_type() for chem_query_strat_type in ChemDBServiceQueryStrategy.subclass_registry.values()]
    if not services: # check if "services" turns out to be an empty collection (either as-passed or because no subclasses are implemented when defaulting)
        raise IndexError('Must provide at least one chemical database querying strategy to "services"')
    n_services_to_try : int = len(services)
    
    # query services sequentially in order of appearance
    for i, service in enumerate(services, start=1):
        ## validate type of service strategies
        if isinstance(service, type):
            service = service() # allows ChemDBServiceQueryStrategy types to be passed in lieu of instances
        if not isinstance(service, ChemDBServiceQueryStrategy):
            raise TypeError(f'Services must be specified as {ChemDBServiceQueryStrategy.__name__} instances, not objects of type {type(service.__name)}')
        
        ## attempt to query result from service
        LOGGER.info(f'Attempting chemical property query to service {i}/{n_services_to_try} ("{service.service_name}"):')
        try:
            prop_val = service.get_property(
                prop_name,
                representation,
                namespace,
                keep_first_only=keep_first_only,
                allow_null_return=allow_null_return,
                **kwargs,
            )
            return prop_val
        except HTTPError:
            LOGGER.error(f'Query to {service.service_name} failed, either due to connection timeout or invalid request')
            continue
        except (InvalidPropertyError, NullPropertyResponse): # skip over invalid property names (keep trying other services rather than failing)
            # log messages baken in to respective raises for these custom exceptions
            continue
    else: # take action when None of the provided services turn up fruitful
        fail_msg = 'Query could not be fulfilled by any of the provided chemical query services'
        if fail_quietly:
            LOGGER.error(f'{fail_msg}; returning NoneType')
            return None
        else: # fail vocally if none of the services can fulfill the property request
            raise ValueError(fail_msg)